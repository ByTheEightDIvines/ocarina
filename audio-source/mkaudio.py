import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, resample_poly, fftconvolve
sr,x=wavfile.read('rec.wav'); x=x.astype(np.float64)/32768
def fade(sig,a,b,sr):
    s=sig.copy(); n=int(a*sr); s[:n]*=np.linspace(0,1,n) if n else 1
    m=int(b*sr); s[len(s)-m:]*=np.linspace(1,0,m)**1.5 if m else 1; return s
x=fade(x,0.004,0.0,sr)
# end of take is clipped mid-note -> soft release
x=fade(x,0,0.14,sr)
t0=4.72; last=x[int(t0*sr):].copy()
D=0.42; gains=[0.72,0.53,0.39,0.28,0.20,0.14]; cut=[6000,5000,4200,3500,3000,2600]
tail_len=len(x)+int(D*sr*len(gains))+int(2.2*sr)
y=np.zeros(tail_len); y[:len(x)]+=x
echo_bus=np.zeros(tail_len)
for k,(g,c) in enumerate(zip(gains,cut),1):
    sos=butter(2,c,'low',fs=sr,output='sos'); e=sosfilt(sos,last)*g
    st=int(t0*sr)+int(D*k*sr); echo_bus[st:st+len(e)]+=e
# canyon wall diffusion: decaying filtered noise IR, ~1.6s
rng=np.random.default_rng(7); L=int(1.6*sr); ir=rng.standard_normal(L)*np.exp(-np.arange(L)/(0.38*sr))
ir=sosfilt(butter(2,[300,5000],'band',fs=sr,output='sos'),ir); ir/=np.sqrt(np.sum(ir**2))
wet=fftconvolve(echo_bus,ir)[:tail_len]*0.35
lastonly=np.zeros(tail_len); lastonly[int(t0*sr):len(x)]=x[int(t0*sr):]
wet+=fftconvolve(lastonly,ir)[:tail_len]*0.18
y+=echo_bus+wet
# trim silence tail
env=np.abs(y); nz=np.where(env>1e-4)[0][-1]; y=y[:nz+int(0.05*sr)]; y=fade(y,0,0.05,sr)
y*=0.89/np.abs(y).max()
y44=resample_poly(y,441,480)
y44*=0.89/np.abs(y44).max()
wavfile.write('build/horse_call_ocarina_preview.wav',44100,(y44*32767).astype(np.int16))
np.save('build/y44.npy',y44); print('len s',len(y44)/44100)
