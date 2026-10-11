"""Conservative interval metadata and bounds for the frozen FP32/RN-FP64 contract."""
import math
import numpy as np

RHO = 1e-4


def error_bound(d=960):
    u = 2.**-53
    gamma = ((4*d+8)*u)/(1-(4*d+8)*u)
    return math.sqrt(gamma*4*d) + u*math.sqrt(4*d)*2


def round32(value, up):
    result = np.asarray(value, dtype=np.float32)
    wrong = result.astype(np.float64) < value if up else result.astype(np.float64) > value
    return np.where(wrong, np.nextafter(result, np.float32(np.inf if up else -np.inf)), result)


def endpoints(minimum, maximum):
    assert error_bound() < RHO
    lo = round32(np.maximum(0.,np.nextafter(minimum-RHO,-np.inf)),False)
    hi = round32(np.nextafter(maximum+RHO,np.inf),True)
    return lo,hi


def bound(low, high, distance):
    qlo = np.maximum(0.,np.nextafter(distance-RHO,-np.inf))
    qhi = np.nextafter(distance+RHO,np.inf)
    left = np.nextafter(low.astype(np.float64)-qhi,-np.inf)
    right = np.nextafter(qlo-high.astype(np.float64),-np.inf)
    raw = np.maximum(0.,np.maximum(left,right))
    return np.maximum(0.,np.nextafter(raw-RHO,-np.inf))


def metadata_size(k, region):
    logical = 8*k + ((6*k+7)//8 if region else 0)
    return logical, ((logical+15)//16)*16


def serialize(low, high, selected, region):
    """Explicit fixed aligned layout: FP32 [lo,hi] pairs, packed six-bit IDs, zeros."""
    r,k = selected.shape
    logical,aligned = metadata_size(k,region)
    out = np.zeros((r,aligned),dtype=np.uint8)
    if not k:
        return out.tobytes()
    ix = np.arange(r)[:,None]
    values = np.stack([low[ix,selected],high[ix,selected]],axis=-1).astype('<f4')
    out[:,:8*k] = values.reshape(r,2*k).view(np.uint8).reshape(r,8*k)
    if region:
        packed = np.zeros(r,dtype=np.uint64)
        for j in range(k):
            packed |= selected[:,j].astype(np.uint64) << (6*j)
        out[:,8*k:logical] = packed.astype('<u8').view(np.uint8).reshape(r,8)[:,:logical-8*k]
    return out.tobytes()
