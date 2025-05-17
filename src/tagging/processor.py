import timm
from typing import Iterable
import torch
from PIL import Image
from torch import Tensor, device, nn
from torchvision.transforms import Compose

from tagging.enums import TagData


def pil_ensure_rgb(image: Image.Image) -> Image.Image:
    if image.mode not in ['RGB', 'RGBA']:
        image = image.convert('RGBA') if 'transparency' in image.info else image.convert('RGB')
    if image.mode == 'RGBA':
        background = Image.new('RGBA', image.size, (255, 255, 255))
        background.alpha_composite(image)
        image = background.convert('RGB')
    return image


def get_tags(probs: Tensor, tag_data: TagData, g_min: float, c_min: float, by_idx=True):
    n_decimals = 3
    probs = [float(p) for p in probs.cpu().numpy()]

    if by_idx:
        rating_tags = {idx: round(probs[idx], n_decimals) for idx in tag_data.rating}
        gen_tags = {idx: round(probs[idx], n_decimals) for idx in tag_data.general if probs[idx] > g_min}
        char_tags = {idx: round(probs[idx], n_decimals) for idx in tag_data.character if probs[idx] > c_min}
    else:
        rating_tags = {tag_data.names[idx]: round(probs[idx], n_decimals) for idx in tag_data.rating}
        gen_tags = {tag_data.names[idx]: round(probs[idx], n_decimals) for idx in tag_data.general if probs[idx] > g_min}
        char_tags = {tag_data.names[idx]: round(probs[idx], n_decimals) for idx in tag_data.character if probs[idx] > c_min}

    return rating_tags, char_tags, gen_tags


def process_images_from_paths(image_paths: Iterable[str], model: nn.Module, transform: Compose, torch_device: device, tag_data: TagData, g_min: float, c_min: float, by_idx: bool=True):
    img_tensors = []
    for image_path in image_paths:
        img = Image.open(image_path)
        img = pil_ensure_rgb(img)
        img_tensor = transform(img).unsqueeze(0).to(torch_device, non_blocking=True)[:, [2, 1, 0]]  # RGB to BGR
        img_tensors.append(img_tensor)

    img_batch = torch.cat(img_tensors, dim=0)

    with torch.inference_mode():
        outputs = torch.sigmoid(model(img_batch))

    return [get_tags(output.squeeze(0), tag_data, g_min, c_min, by_idx=by_idx) for output in outputs]


def process_images_from_imgs(imgs: list[Image.Image], model: nn.Module, transform: Compose, torch_device: device, tag_data: TagData, g_min: float, c_min: float, by_idx: bool=True):
    img_tensors = []
    for img in imgs:
        img = pil_ensure_rgb(img)
        img_tensor = transform(img).unsqueeze(0).to(torch_device, non_blocking=True)[:, [2, 1, 0]]  # RGB to BGR
        img_tensors.append(img_tensor)

    img_batch = torch.cat(img_tensors, dim=0)

    with torch.inference_mode():
        outputs = torch.sigmoid(model(img_batch))

    return [get_tags(output.squeeze(0), tag_data, g_min, c_min, by_idx=by_idx) for output in outputs]


def load_model(tag_model_repo_id: str) -> nn.Module:
    model = timm.create_model(f'hf-hub:{tag_model_repo_id}', pretrained=True).eval()
    model.load_state_dict(timm.models.load_state_dict_from_hf(tag_model_repo_id))
    return model
