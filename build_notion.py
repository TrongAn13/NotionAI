import csv, io, json, os, re, sys, time, zipfile, getpass
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

PARENT_ID='401de7f296f680c99145c4077252d990'
API='https://api.notion.com/v1'
VERSION='2025-09-03'
ZIP=Path(__file__).with_name('Starter_Pack.zip')

DATE={'Date','Due Date','Target Date','Start Date','Issue Date','Publish Date','Next Follow Up','Week Starting'}
NUM={'Amount','Budget','Target Amount','Saved Amount','Opening Balance','Credits','Estimated Hours','Duration Minutes','Goal Per Week','Score Out Of 10','Views','Likes','Comments','Subscribers Gained','Watch Time Hours','Fee','Estimated Value'}
SELECT={'Type','Category','Account','Status','Priority','Semester','Platform','Niche','Pillar','Script Status','Voice Status','Edit Status','Publish Status','Payment Status','Stage','Area','Frequency','Service'}
CHECK={'Completed'}
URL={'URL','Video URL'}
EMAIL={'Email'}

def rt(s): return [{'type':'text','text':{'content':str(s)[:1900]}}]
def block(kind,s): return {'object':'block','type':kind,kind:{'rich_text':rt(s)}}
def request(method,path,token,payload=None):
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    headers={'Authorization':'Bearer '+token,'Notion-Version':VERSION,'Content-Type':'application/json'}
    for attempt in range(6):
        req=Request(API+path,data=data,headers=headers,method=method)
        try:
            with urlopen(req,timeout=40) as resp: return json.loads(resp.read().decode())
        except HTTPError as e:
            body=e.read().decode('utf-8','replace')
            if e.code==429 and attempt<5:
                time.sleep(int(e.headers.get('Retry-After','2'))+1);continue
            if e.code>=500 and attempt<5: time.sleep(2**attempt);continue
            raise RuntimeError(f'Notion API {e.code} {path}: {body[:600]}')
        except URLError as e:
            if attempt<5: time.sleep(2**attempt);continue
            raise RuntimeError(str(e))

def prop_type(name,first):
    if name in DATE: return 'date'
    if name in NUM: return 'number'
    if name in CHECK: return 'checkbox'
    if name in URL: return 'url'
    if name in EMAIL: return 'email'
    if name in SELECT or name.endswith(' Status'): return 'select'
    return 'rich_text'

def property_value(kind,v):
    if kind=='title': return {'title':rt(v or 'Untitled')}
    if not v: return None
    if kind=='number':
        try:return {'number':float(v)}
        except ValueError:return None
    if kind=='checkbox':return {'checkbox':v.lower() in ('true','yes','1')}
    if kind=='date':return {'date':{'start':v}}
    if kind=='select':return {'select':{'name':v[:100]}}
    if kind=='url':return {'url':v} if v.startswith(('http://','https://')) else None
    if kind=='email':return {'email':v}
    return {'rich_text':rt(v)}

def main():
    if not ZIP.exists():sys.exit('Missing Starter_Pack.zip next to script')
    token=os.getenv('NOTION_API_TOKEN','').strip() or getpass.getpass('Paste Notion API token (hidden, never shared): ').strip()
    if not token:sys.exit('No token provided')
    page=request('GET','/pages/'+PARENT_ID,token)
    print('Connected. Target page ID:',page['id'])
    print('This will CREATE 5 new child pages, 22 databases and sample rows. It will not delete existing content.')
    if input('Type CREATE to continue: ').strip()!='CREATE':sys.exit('Cancelled')
    with zipfile.ZipFile(ZIP) as z:
        paths=z.namelist()
        folders=sorted({p.split('/')[1] for p in paths if p.startswith('notion_template_starter_pack/') and p.endswith('/Dashboard.md')})
        for folder in folders:
            prefix='notion_template_starter_pack/'+folder+'/'
            title=folder.split('_',1)[1].replace('_',' ')
            print('\nCreating:',title,flush=True)
            children=[block('heading_1',title),block('paragraph','Customizable starter template • fictional sample data'),block('heading_2','Start here'),block('paragraph','Explore the databases below. Customize their views, relations and layout in Notion before selling.')]
            page=request('POST','/pages',token,{'parent':{'type':'page_id','page_id':PARENT_ID},'properties':{'title':{'type':'title','title':rt(title)}},'children':children})
            child_id=page['id']
            csvs=sorted(p for p in paths if p.startswith(prefix) and p.endswith('.csv'))
            for path in csvs:
                name=Path(path).stem.replace('_',' ')
                rows=list(csv.DictReader(io.StringIO(z.read(path).decode('utf-8-sig'))))
                if not rows:continue
                headers=list(rows[0]); types={h:('title' if i==0 else prop_type(h,rows[0].get(h,''))) for i,h in enumerate(headers)}
                schema={h:{t:{}} for h,t in types.items()}
                db=request('POST','/databases',token,{'parent':{'type':'page_id','page_id':child_id},'title':rt(name),'initial_data_source':{'properties':schema}})
                ds=(db.get('data_sources') or [{}])[0].get('id')
                if not ds: raise RuntimeError('No data_source id in response: '+str(db)[:400])
                for row in rows:
                    props={}
                    for h,v in row.items():
                        p=property_value(types[h],v)
                        if p is not None:props[h]=p
                    request('POST','/pages',token,{'parent':{'type':'data_source_id','data_source_id':ds},'properties':props})
                    time.sleep(0.36)
                print('  +',name,'(',len(rows),'sample rows )',flush=True)
                time.sleep(0.36)
            text=z.read(prefix+'Dashboard.md').decode('utf-8')
            blocks=[block('heading_2','Suggested setup')]
            for line in text.splitlines():
                if line.startswith('## '): blocks.append(block('heading_3',line[3:]))
                elif line.startswith('- '): blocks.append(block('bulleted_list_item',line[2:]))
                elif line.strip() and not line.startswith(('#','>')): blocks.append(block('paragraph',line))
            for i in range(0,len(blocks),90):
                request('PATCH','/blocks/'+child_id+'/children',token,{'children':blocks[i:i+90]})
            print('  Page:',page.get('url',''),flush=True)
    print('\nDONE. Open My Template Store in Notion. Finish views, formulas and relations manually.')

if __name__=='__main__':
    try:main()
    except (RuntimeError,KeyboardInterrupt) as e:
        print('\nStopped:',e,'\nExisting created content is preserved. Do not rerun blindly; it may duplicate pages.')
        sys.exit(1)
