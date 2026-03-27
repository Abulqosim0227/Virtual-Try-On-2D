"""CatVTON model utilities. Source: github.com/Zheng-Chong/CatVTON (CC BY-NC-SA 4.0)."""

import torch

from vto.pipeline.models.catvton_lib.attn_processor import AttnProcessor2_0, SkipAttnProcessor


def init_adapter(unet, cross_attn_cls=SkipAttnProcessor, self_attn_cls=None,
                 cross_attn_dim=None, **kwargs):
    if cross_attn_dim is None:
        cross_attn_dim = unet.config.cross_attention_dim
    attn_procs = {}
    for name in unet.attn_processors.keys():
        cross_attention_dim = None if name.endswith("attn1.processor") else cross_attn_dim
        if name.startswith("mid_block"):
            hidden_size = unet.config.block_out_channels[-1]
        elif name.startswith("up_blocks"):
            block_id = int(name[len("up_blocks.")])
            hidden_size = list(reversed(unet.config.block_out_channels))[block_id]
        elif name.startswith("down_blocks"):
            block_id = int(name[len("down_blocks.")])
            hidden_size = unet.config.block_out_channels[block_id]
        if cross_attention_dim is None:
            if self_attn_cls is not None:
                attn_procs[name] = self_attn_cls(
                    hidden_size=hidden_size, cross_attention_dim=cross_attention_dim, **kwargs
                )
            else:
                attn_procs[name] = AttnProcessor2_0(
                    hidden_size=hidden_size, cross_attention_dim=cross_attention_dim, **kwargs
                )
        else:
            attn_procs[name] = cross_attn_cls(
                hidden_size=hidden_size, cross_attention_dim=cross_attention_dim, **kwargs
            )
    unet.set_attn_processor(attn_procs)
    return torch.nn.ModuleList(unet.attn_processors.values())


def get_trainable_module(unet, name):
    if name == "attention":
        attn_blocks = torch.nn.ModuleList()
        for module_name, param in unet.named_modules():
            if "attn1" in module_name:
                attn_blocks.append(param)
        return attn_blocks
    raise ValueError(f"Unknown trainable_module_name: {name}")
