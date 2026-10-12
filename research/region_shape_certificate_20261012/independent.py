"""Separate ordered reference for frozen original-vector G5 pairs and public fixtures."""
import math
import numpy as np

ETA = 1e-8
RHO = 1e-4
QUERY_ERROR = math.nextafter(math.nextafter(math.sqrt(8.), math.inf) * ETA, math.inf)


def upper(x):
    return math.nextafter(x, math.inf)


def lower(x):
    return max(0., math.nextafter(x, -math.inf))


def f32up(v):
    f = np.float32(v)
    return np.nextafter(f,np.float32(np.inf)) if float(f) < v else f


def f32down(v):
    f = np.float32(v)
    return np.nextafter(f,np.float32(-np.inf)) if float(f) > v else f


def norm_up(values):
    total = 0.
    for value in values:
        v = float(value); total = upper(total + upper(v*v))
    return upper(math.sqrt(total))


def norm_lo(values):
    total = 0.
    for value in values:
        v = float(value); total = lower(total + lower(v*v))
    return lower(math.sqrt(total))


def distances(points, c):
    result=np.zeros(len(points))
    for j in range(8):
        difference=points[:,j]-float(c[j]);term=difference*difference
        result=result+term
    return result


def reference_shapes(points):
    n=len(points);raw=[]
    for j in range(8):
        total=0.
        for value in points[:,j]:total=total+float(value)
        raw.append(total/n)
    raw=np.array(raw);c=raw.astype(np.float32)
    current=raw.copy();best=raw.copy();bestscore=float(distances(points,current).max())
    for iteration in range(1,65):
        scores=distances(points,current);far=int(np.argmax(scores))
        current=np.array([current[j]+(float(points[far,j])-current[j])/(iteration+1) for j in range(8)])
        score=float(distances(points,current).max())
        if score<bestscore:best=current.copy();bestscore=score
    mc=best.astype(np.float32)
    deviations=[];mdeviations=[]
    for z in points:
        deviations.append([upper(upper(abs(float(z[j])-float(c[j])))+ETA) for j in range(8)])
        mdeviations.append([upper(upper(abs(float(z[j])-float(mc[j])))+ETA) for j in range(8)])
    radius=f32up(max(map(norm_up,deviations)));mradius=f32up(max(map(norm_up,mdeviations)))
    scale=np.array([f32up(max(v[j] for v in deviations)) for j in range(8)],dtype=np.float32)
    factor=f32up(max(norm_up([upper(v[j]/float(scale[j])) for j in range(8)]) for v in deviations))
    lo=np.array([f32down(math.nextafter(min(map(float,points[:,j]))-ETA,-math.inf)) for j in range(8)],dtype=np.float32)
    hi=np.array([f32up(upper(max(map(float,points[:,j]))+ETA)) for j in range(8)],dtype=np.float32)
    return dict(low=lo,high=hi,center=c,radius=np.array(radius),minimax=mc,minimax_radius=np.array(mradius),scale=scale,factor=np.array(factor))


def ball_lb(c,r,q):
    gaps=[lower(abs(float(q[j])-float(c[j]))) for j in range(8)]
    return lower(lower(lower(norm_lo(gaps)-float(r))-QUERY_ERROR)-RHO)


def ellipsoid_lb(c,s,r,q):
    c=list(map(float,c));s=list(map(float,s));r=float(r);d=[float(q[j])-c[j] for j in range(8)]
    normalized=0.;weighted=0.
    for j in range(8):
        term=d[j]/s[j];normalized=normalized+term*term
        term=s[j]*d[j];weighted=weighted+term*term
    left=0.;right=math.sqrt(weighted)/r
    for _ in range(64):
        mid=(left+right)/2;value=0.
        for j in range(8):
            term=s[j]*d[j]/(s[j]*s[j]+mid);value=value+term*term
        if value>r*r:left=mid
        else:right=mid
    lam=0. if normalized<=r*r else (left+right)/2
    total=0.
    for j in range(8):
        abslo=lower(abs(float(q[j])-c[j]));numerator=lower(lam*lower(abslo*abslo))
        denom=upper(upper(s[j]*s[j])+lam);total=lower(total+lower(numerator/denom))
    dual=lower(total-upper(lam*upper(r*r)))
    return lower(lower(lower(math.sqrt(dual))-QUERY_ERROR)-RHO)


def box_lb(lo,hi,q):
    total=0.
    for j in range(8):
        qlo=math.nextafter(float(q[j])-ETA,-math.inf);qhi=upper(float(q[j])+ETA)
        gap=max(0.,math.nextafter(float(lo[j])-qhi,-math.inf),math.nextafter(qlo-float(hi[j]),-math.inf))
        term=lower(gap*gap);total=max(total,lower(total+term))
    return lower(math.nextafter(math.sqrt(total),-math.inf)-RHO)


def project(points,basis):
    result=np.zeros((len(points),8))
    for j in range(8):
        column=np.zeros(len(points))
        for d in range(960):
            product=points[:,d].astype(np.float64)*float(basis[j,d]);column=column+product
        result[:,j]=column
    return result


def original_score(points,q):
    result=np.zeros(len(points))
    for d in range(960):
        delta=points[:,d].astype(np.float64)-float(q[d]);term=delta*delta
        result=result+term
    return result
