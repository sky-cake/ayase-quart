import subprocess
import os
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from enum import Enum
from werkzeug.security import safe_join
import requests

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.graphs import Graph


file_exts = ['jpg', 'png', 'webm', 'mp4',]
pattern_tld = r'\.(' + '|'.join(file_exts) + r')\b'
def replace_file_exts(text):
    return re.sub(pattern_tld, lambda m: f' dot {m.group(1)}', text)


def replace_with_domain_and_tld(text):
    """
    - `https://www.privacyguides.org/en/tools/ -> privacyguides   dot org`
    - `http://sub.anonymousplanet.jp?omg=1     -> anonymousplanet dot jp`
    """
    def repl(match):
        url = match.group(0)
        if url.startswith('http'):
            hostname = urlparse(url).hostname
        else:
            hostname = url
        if not hostname or '.' not in hostname:
            return url
        parts = hostname.split('.')
        if len(parts) >= 2:
            domain = parts[-2]
            tld = parts[-1]
            return f'link to {domain} dot {tld}'
        return url
    pattern = r'https?:\/\/[^\s]+\.[^\s]+'
    return re.sub(pattern, repl, text)


def clean_text(text: str) -> str:
    if not text:
        return text
    text = BeautifulSoup(text, features="html.parser").text.strip()
    text = re.sub(r'>>\d+(?: \(OP\))?', ' ', text)
    text = replace_with_domain_and_tld(text)
    text = replace_file_exts(text)
    return text


class Speaker(Enum):
    narrator = 1
    anon = 2


def make_filename(board: str, post_num: str) -> str:
    return f'{board}{post_num}.wav'


class TranscriptMode(Enum):
    dfs=1
    bfs=2
    op=3
    op_and_replies_to_op=4


def get_post_num_order(g: Graph, mode: TranscriptMode) -> list[int]:
    match mode:
        case TranscriptMode.dfs:
            return g.get_dfs()
        case TranscriptMode.bfs:
            return g.get_bfs()
        case TranscriptMode.op:
            return g.get_op()
        case TranscriptMode.op_and_replies_to_op:
            return g.get_op_and_replies_to_op()
        case _:
            return g.get_op_and_replies_to_op()


def get_vox_filepath(vox_root_path: str, board: str, num: int, ext: str) -> str:
    return safe_join(vox_root_path, board, f'{num}.{ext}')


def make_transcript(g: Graph, mode: TranscriptMode) -> str:
    """Returns the graph of posts with added narration text, and cleaned post text, ready for tts."""
    order = get_post_num_order(g, mode)

    is_op = 1
    texts = []
    for pnum in order:
        post = g.num_2_posts[pnum]
        if is_op:
            if post['title']:
                texts.append((Speaker.narrator, 'O P Subject: '))
                texts.append((Speaker.anon, post['title']))

            if post['comment']:
                texts.append((Speaker.narrator, 'O P Comment: '))
                texts.append((Speaker.anon, post['comment']))

            if len(order) == 1:
                texts.append((Speaker.narrator, 'No replies to O P.'))
                return ' '.join(t[1] for t in texts)

            is_op = 0
        else:
            name = 'Anon' if post['name'] == 'Anonymous' else post['name']
            texts.append((Speaker.narrator, f'{name}: '))
            texts.append((Speaker.anon, post['comment']))

    return clean_text(' '.join(t[1] for t in texts if t[1])) if texts else ''


class VoxIO:
    def read(self, text: str):
        """Read the text to speakers"""
        raise NotImplementedError()

    def write(self, text: str, filepath: str):
        """Write the tts to a .wav file."""
        raise NotImplementedError()


class VoiceFlite(str, Enum):
    MANBOT = "cmu_us_bdl"
    SIRI = "cmu_us_clb"
    SOYJAK = "cmu_us_aew"
    FEMBOT = "cmu_us_slt"
    BRITBONG = "cmu_us_fem"
    SANGITA = "cmu_indic_pan_amp"

    # voices = {
    ## best voices
    # "cmu_us_bdl": "Manbot (M)",
    # "cmu_us_clb": "Siri (F)",
    # "cmu_us_aew": "Soyjak (M)",

    ## decent voices
    # "cmu_us_slt": "Fembot (F)",
    # "cmu_us_fem": "Britbong (M)",
    # "cmu_indic_pan_amp": "Sangita (F)",

    ## bad voices
    # "cmu_us_ahw": "US English - AHW",
    # "cmu_us_aup": "US English - AUP",
    # "cmu_us_awb": "US English - AWB",
    # "cmu_us_axb": "US English - AXB",
    # "cmu_us_eey": "US English - EEY",
    # "cmu_us_gka": "US English - GKA",
    # "cmu_us_jmk": "US English - JMK",
    # "cmu_us_ksp": "US English - KSP",
    # "cmu_us_ljm": "US English - LJM",
    # "cmu_us_lnh": "US English - LNH",
    # "cmu_us_rms": "US English - RMS",
    # "cmu_us_rxr": "US English - RXR",
    # "cmu_us_slp": "US English - SLP",
    # "cmu_indic_ben_rm": "Bengali - RM",
    # "cmu_indic_guj_ad": "Gujarati - AD",
    # "cmu_indic_guj_dp": "Gujarati - DP",
    # "cmu_indic_guj_kt": "Gujarati - KT",
    # "cmu_indic_hin_ab": "Hindi - AB",
    # "cmu_indic_kan_plv": "Kannada - PLV",
    # "cmu_indic_mar_aup": "Marathi - AUP",
    # "cmu_indic_mar_slp": "Marathi - SLP",
    # "cmu_indic_tam_sdr": "Tamil - SDR",
    # "cmu_indic_tel_kpn": "Telugu - KPN",
    # "cmu_indic_tel_sk": "Telugu - SK",
    # "cmu_indic_tel_ss": "Telugu - SS",
    # }


class VoxFlite(VoxIO):
    """
    - https://github.com/festvox/flite
    - https://www.cs.cmu.edu/~awb/festival_demos/general.html
    - http://festvox.org/packed/festival/2.4/voices/
    """

    def __init__(self, conf):
        self.conf = conf

    def get_suggested_pitch(voice: VoiceFlite):
        return {
            VoiceFlite.MANBOT: 105,
            VoiceFlite.SIRI: 105,
            VoiceFlite.SOYJAK: 100,
            VoiceFlite.FEMBOT: 115,
            VoiceFlite.BRITBONG: 90,
            VoiceFlite.SANGITA: 80,
        }.get(voice, 100)

    def read(
        self,
        text: str = None,
        voice: VoiceFlite = VoiceFlite.MANBOT,
        spoken_speed: float = 1.2,
        spoken_pitch: float = 115,
        use_suggested_pitch: bool = True,
        print_words: bool = False,
    ):
        """If `use_suggested_pitch = True` then `spoken_pitch` is omitted."""
        cmd = self.get_tts_command(
            text=text,
            text_filepath=None,
            voice=voice,
            spoken_speed=spoken_speed,
            spoken_pitch=spoken_pitch,
            use_suggested_pitch=use_suggested_pitch,
            print_words=print_words,
            wav_output_filepath=None,
        )
        subprocess.call(cmd)

    def write(
        self,
        text: str = None,
        voice: VoiceFlite = VoiceFlite.MANBOT,
        spoken_speed: float = 1.2,
        spoken_pitch: float = 115,
        use_suggested_pitch: bool = True,
        wav_output_filepath: str=None,
    ):
        """If `use_suggested_pitch = True` then `spoken_pitch` is omitted."""
        if not wav_output_filepath:
            raise ValueError(wav_output_filepath)
        
        dname = os.path.dirname(wav_output_filepath)
        if not os.path.isdir(dname):
            os.makedirs(dname)

        cmd = self.get_tts_command(
            text=text,
            text_filepath=None,
            voice=voice,
            spoken_speed=spoken_speed,
            spoken_pitch=spoken_pitch,
            use_suggested_pitch=use_suggested_pitch,
            print_words=False,
            wav_output_filepath=wav_output_filepath,
        )
        subprocess.call(cmd)

    def get_tts_command(
        self,
        text: str = None,
        text_filepath: str = None,
        voice: VoiceFlite = VoiceFlite.MANBOT,
        spoken_speed: float = 1.2,
        spoken_pitch: float = 100,
        use_suggested_pitch: bool = True,
        print_words: bool = False,
        wav_output_filepath: str = None,
    ):
        """`~/Desktop/flite/bin/flite -voice ~/Desktop/flite/voices/cmu_us_clb.flitevox -pw --setf int_f0_target_mean=115 --setf duration_stretch=1.3 ~/Desktop/sentences.txt`"""

        if not text and not text_filepath:
            raise ValueError(text, text_filepath)

        flitevox_path = safe_join(self.conf['path_to_flite_voices'], voice.value + '.flitevox')
        use_voice = os.path.isfile(flitevox_path)

        cmd = [self.conf['path_to_flite_binary']]

        if use_voice:
            cmd.extend(['-voice', flitevox_path])

        if print_words:
            cmd.append('-pw')

        if spoken_pitch:
            cmd.append(f'--setf')
            if use_suggested_pitch:
                spoken_pitch = VoxFlite.get_suggested_pitch(voice)
            else:
                spoken_pitch = int(spoken_pitch)
            cmd.append(f'int_f0_target_mean={spoken_pitch}')

        if spoken_speed:
            cmd.append(f'--setf')
            cmd.append(f'duration_stretch={1 / float(spoken_speed)}')

        if text:
            cmd.append(text)
        elif text_filepath:
            if ' ' in text_filepath:
                raise ValueError(text_filepath, 'Cannot contain spaces. https://github.com/festvox/flite#usage')
            cmd.append(text_filepath)

        if wav_output_filepath:
            cmd.append(wav_output_filepath)

        return cmd

    def sample_all_voices(self):
        text = clean_text(
            """
            Follow these hyperlinks and reveal exquisite ascii...
            Tools: https://www.privacyguides.org/en/tools/ Hitchhiker's Guide: https://anonymousplanet.org/guide.html
            """
        )

        self.read(text=text, voice=VoiceFlite.SIRI, print_words=True)
        self.read(text=text, voice=VoiceFlite.MANBOT, print_words=True)
        self.read(text=text, voice=VoiceFlite.SOYJAK, print_words=True)
        self.read(text=text, voice=VoiceFlite.FEMBOT, print_words=True)
        self.read(text=text, voice=VoiceFlite.BRITBONG, print_words=True)
        self.read(text=text, voice=VoiceFlite.SANGITA, print_words=True)


class VoxKokoro(VoxIO):
    def write(self, text: str, filepath: str):
        response = requests.post(
            "http://localhost:8880/v1/audio/speech",
            json={
                "model": "kokoro",  
                "input": text,
                "voice": "af_bella",
                "response_format": "mp3",  # mp3, wav, opus, flac
                "speed": 1.0
            }
        )

        dname = os.path.dirname(filepath)
        if not os.path.isdir(dname):
            os.makedirs(dname)

        with open(filepath, "wb") as f:
            f.write(response.content)


if __name__ == '__main__':
    d = dict(
        enabled = True,
        path_to_flite_binary = '/home/dolphin/Desktop/flite/bin/flite',
        path_to_flite_voices = '/home/dolphin/Desktop/flite/voices',
        voice_narrator = VoiceFlite.MANBOT,
        voice_anon = VoiceFlite.MANBOT,
    )

    VoxFlite(d).sample_all_voices()
