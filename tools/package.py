"""Build a source-copy/add binary delta. Never ship full original game assets."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile
import uuid
from build_locale import ROOT, load

VERSION='0.1.0-beta.3'
PACKAGE='VernalEdge-Korean-'+VERSION

def sha(raw):return hashlib.sha256(raw).hexdigest()

def common_prefix(a,b):
    low,high=0,min(len(a),len(b))
    while low<high:
        mid=(low+high+1)//2
        if a[:mid]==b[:mid]:low=mid
        else:high=mid-1
    return low

def common_suffix(a,b,limit):
    low,high=0,limit
    while low<high:
        mid=(low+high+1)//2
        if a[-mid:]==b[-mid:]:low=mid
        else:high=mid-1
    return low

def chunk_ranges(raw):
    result={};pos=8
    assert raw[:4]==b'FORM'
    while pos<len(raw):
        tag,length=struct.unpack_from('<4sI',raw,pos)
        result[tag.decode('ascii')]=(pos,8+length)
        pos+=8+length
    assert pos==len(raw)
    return result

def delta(original,patched,folder,gamemaker=False):
    operations=[]
    def add(raw):
        if not raw:return
        blob=gzip.compress(raw,compresslevel=9,mtime=0)
        name=sha(blob)
        (folder/(name+'.gz')).write_bytes(blob)
        operations.append(dict(type='add',blob=name,length=len(raw)))
    def copy(offset,length):
        if length:operations.append(dict(type='copy',offset=offset,length=length))
    def segment(before,after,offset):
        prefix=common_prefix(before,after)
        suffix=common_suffix(before,after,min(len(before),len(after))-prefix)
        copy(offset,prefix)
        add(after[prefix:len(after)-suffix if suffix else len(after)])
        copy(offset+len(before)-suffix,suffix)
    if gamemaker:
        old,new=chunk_ranges(original),chunk_ranges(patched)
        if list(old)!=list(new):raise ValueError('Chunk ordering changed')
        segment(original[:8],patched[:8],0)
        for tag,(newpos,newlen) in new.items():
            oldpos,oldlen=old[tag]
            segment(original[oldpos:oldpos+oldlen],patched[newpos:newpos+newlen],oldpos)
    elif original:
        segment(original,patched,0)
    else:add(patched)
    return operations

def reconstruct(original,operations,folder):
    result=bytearray()
    for op in operations:
        if op['type']=='copy':result.extend(original[op['offset']:op['offset']+op['length']])
        else:
            raw=gzip.decompress((folder/(op['blob']+'.gz')).read_bytes())
            assert len(raw)==op['length'];result.extend(raw)
    return bytes(result)

def build(replace=False):
    builddir=ROOT/'private/build'
    mode=load(builddir/'locale-mode.json')
    report=load(builddir/'validation.json')
    if report['errors'] or report['untranslated'] or report['full_locale_missing_glyphs']:
        raise ValueError('Translation/static validation is incomplete')
    package=ROOT/'dist'/PACKAGE
    if package.exists():
        if not replace:
            raise FileExistsError('Package output exists; --replace archives the prior generated package: '+str(package))
        if load(package/'manifest.json')['package']!=PACKAGE:
            raise ValueError('Not a recognized generated package')
        previous=ROOT/'private/previous-packages'/uuid.uuid4().hex
        for path in (package,previous):
            if not path.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Unsafe package archive path')
        previous.parent.mkdir(parents=True,exist_ok=True)
        package.rename(previous)
        oldzip=ROOT/'dist'/(PACKAGE+'.zip')
        if oldzip.exists():shutil.copy2(oldzip,previous/'previous-package.zip')
    payload=package/'payload';payload.mkdir(parents=True,exist_ok=True)
    originalmanifest=load(ROOT/'private/original/manifest.json')
    manifest=dict(format=1,package=PACKAGE,version=VERSION,appid=1546710,buildid='10939741',
        exe=originalmanifest['files']['VernalEdge.exe']['sha256'],localeMode=mode['mode'],
        releaseReady=False,files=[])
    for name in ['data.win','loc/available.json','loc/'+mode['locale']]:
        src=ROOT/'private/original'/name
        original=src.read_bytes() if src.exists() else b''
        patched=(builddir/name).read_bytes()
        ops=delta(original,patched,payload,gamemaker=name=='data.win')
        assert reconstruct(original,ops,payload)==patched
        manifest['files'].append(dict(path=name,original=sha(original) if src.exists() else None,
            patched=sha(patched),size=len(patched),operations=ops))
        print(name,len(ops),'operations; reconstruction SHA256 verified',flush=True)
    (package/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    for path in (ROOT/'installer').glob('*'):
        if path.is_file():shutil.copy2(path,package/path.name)
    for filename in ('README.ko.md','THIRD_PARTY_NOTICES.md','CHANGELOG.md'):
        shutil.copy2(ROOT/'docs'/filename,package/filename)
    shutil.copy2(ROOT/'private/vendor/galmuri/LICENSE.txt',package/'Galmuri-LICENSE.txt')
    shutil.copy2(ROOT/'docs/QA.md',package/'QA.md')
    shutil.copy2(ROOT/'docs/FULL_REVIEW.md',package/'FULL_REVIEW.md')
    shutil.copy2(builddir/'validation.json',package/'validation.json')
    # Provide the editable translation without including the copyrighted game bundle.
    shutil.copy2(builddir/'loc'/mode['locale'],package/'ko-KR.json')
    shutil.copy2(builddir/'loc/available.json',package/'available.json')
    archive=package.parent/(package.name+'.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for path in sorted(package.rglob('*')):
            if path.is_file():output.write(path,arcname=str(Path(PACKAGE)/path.relative_to(package)))
    (archive.parent/(archive.name+'.sha256')).write_text(sha(archive.read_bytes())+'  '+archive.name+'\n',encoding='ascii')
    print('Package:',archive,'bytes:',archive.stat().st_size,flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--replace',action='store_true')
    build(parser.parse_args().replace)
