# should move to configs or somewhere else for customizability
def media_fs_partition(filename: str) -> str:
    return f'{filename[0:4]}/{filename[4:6]}/{filename}'