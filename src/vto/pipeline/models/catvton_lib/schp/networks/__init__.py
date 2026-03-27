from vto.pipeline.models.catvton_lib.schp.networks.AugmentCE2P import resnet101

__factory = {'resnet101': resnet101}


def init_model(name, *args, **kwargs):
    if name not in __factory:
        raise KeyError(f"Unknown model arch: {name}")
    return __factory[name](*args, **kwargs)
