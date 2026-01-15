"""
PyTorch compatibility patches for pyannote.audio with PyTorch 2.6+
"""

import torch

def patch_torch_load():
    """Patch torch.load to handle pyannote models with PyTorch 2.6+"""
    
    # Add safe globals for TorchVersion
    if hasattr(torch, 'serialization'):
        try:
            torch.serialization.add_safe_globals([torch.torch_version.TorchVersion])
        except:
            pass
    
    # Store original load function
    _original_load = torch.load
    
    # Create patched version that sets weights_only=False for trusted sources
    def _patched_load(*args, **kwargs):
        # For pyannote models (trusted source), disable weights_only check
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_load(*args, **kwargs)
    
    # Replace torch.load globally
    torch.load = _patched_load
    
    return _original_load


def restore_torch_load(original_load):
    """Restore original torch.load function"""
    torch.load = original_load
