import numpy as np, struct
COEF=np.array([(0,0),(0x0800,0),(0,0x0800),(0x0400,0x0400),(0x1000,-0x0800),(0x0e00,-0x0600),(0x0c00,-0x0400),(0x1200,-0x0a00),
      (0x1068,-0x08c8),(0x12c0,-0x0b40),(0x1400,-0x0c00),(0x0800,-0x0800),(0x0400,-0x0400),(-0x0400,0x0400),(-0x0400,0),(-0x0800,0)],dtype=np.int64)
def dec_frame(fr,h1,h2):
    hdr=fr[0]; sc=1<<(hdr>>4); c1,c2=COEF[hdr&15]; out=[]
    for b in fr[1:]:
        for n in (b>>4,b&15):
            n=n-16 if n>=8 else n
            s=((n*sc)<<11)+c1*h1+c2*h2; s>>=11; s=max(-32768,min(32767,s)); out.append(s); h2=h1; h1=s
    return out,h1,h2
def encode(pcm):
    pcm=np.asarray(pcm,np.int64); n=len(pcm); nf=(n+15)//16; pcm=np.concatenate([pcm,np.zeros(nf*16-n,np.int64)])
    combos=[(e,i) for e in range(16) for i in range(16)]
    E=np.array([c[0] for c in combos]); I=np.array([c[1] for c in combos]); SC=(1<<E); C1=COEF[I,0]; C2=COEF[I,1]
    out=bytearray(); h1=h2=0; hist=[]
    for f in range(nf):
        x=pcm[f*16:f*16+16]
        a1=np.full(256,h1); a2=np.full(256,h2); err=np.zeros(256); nib=np.zeros((256,16),np.int64)
        for k in range(16):
            pred=C1*a1+C2*a2
            q=np.round(((x[k]<<11)-pred)/(SC<<11)).astype(np.int64); q=np.clip(q,-8,7)
            s=((q*SC)<<11)+pred; s>>=11; s=np.clip(s,-32768,32767)
            err+=(s-x[k])**2; nib[:,k]=q; a2=a1; a1=s
        b=int(np.argmin(err)); e,i=combos[b]
        fr=bytes([(e<<4)|i])+bytes(((int(nib[b,2*j])&15)<<4)|(int(nib[b,2*j+1])&15) for j in range(8))
        hist.append((h1,h2)); out+=fr
        _,h1,h2=dec_frame(fr,h1,h2)
    return bytes(out),hist
def write_ast(path,pcm,sr):
    data,hist=encode(pcm); n=len(pcm)
    BS=10080; fpb=BS//9; blocks=[]; o=0; fi=0
    while o<len(data):
        chunk=data[o:o+BS]; h1,h2=hist[fi]
        pad=(len(chunk)+31)//32*32
        blocks.append(b'BLCK'+struct.pack('>I',pad)+struct.pack('>hh',h1,h2)+bytes(20)+chunk+bytes(pad-len(chunk)))
        o+=BS; fi+=fpb
    body=b''.join(blocks)
    hdr=struct.pack('>4sIHHHHIIIII',b'STRM',len(body),0,16,1,0,sr,n,0,n,BS)+struct.pack('>I',0)+bytes([0x7f])+bytes(0x40-0x29)
    open(path,'wb').write(hdr+body)
def read_ast(path,ch_sel=0):
    d=open(path,'rb').read(); n=struct.unpack('>I',d[0x14:0x18])[0]; ch=struct.unpack('>H',d[0x0C:0x0E])[0]; o=0x40; out=[]; h1=h2=0
    while o<len(d):
        sz=struct.unpack('>I',d[o+4:o+8])[0]; blk=d[o+0x20+sz*ch_sel:o+0x20+sz*(ch_sel+1)]
        for f in range(0,len(blk)-8,9):
            s,h1,h2=dec_frame(blk[f:f+9],h1,h2); out+=s
        o+=0x20+sz*ch
    return np.array(out[:n])
