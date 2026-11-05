import {useEffect,useState} from 'react';
import {AttachmentList,AttachmentPicker,shareBody} from './attachments';
import {cleanAttachments} from '@/lib/files-store';
import type {MeetingAccess} from '@/lib/meetings';
import {collection,doc,query,orderBy,limit,onSnapshot,setDoc,updateDoc,deleteDoc,serverTimestamp} from 'firebase/firestore';
import {db} from '@/lib/firebase';
import {meetingBodies} from '@/lib/meetings';
import {friendlyError} from '@/lib/store';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import {Plus,MessageSquare,ArrowUpRight,Pencil,Trash2,Paperclip,Newspaper,Send,ChevronRight} from 'lucide-react';
import {toast} from 'sonner';
import {GoalPicker,GoalLabels} from './goal-picker';
import {linkedGroups,isDecadeWide} from '@/lib/decade-goals';
import {eventAccent,accentStyle} from '@/lib/event-style';
import {CreatedBy,usePerson} from './people-context';
import {MemberAvatar} from './member-avatar';

const iso=(v:any)=>v?.toDate?v.toDate().toISOString():typeof v==='string'?v:'';
const day=(v:any)=>{const s=iso(v);return s?new Date(s).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'';};
const group=(p:any)=>p.bodyId||(p.wg?`wg${p.wg}`:'');
const shortBody=(id:string)=>/^wg[1-5]$/.test(id)?`WG${id[2]}`:id==='alliance'?'Alliance':id.toUpperCase();
/** Colour and label of a news item: its Working Group or body, otherwise the Overarching Challenges of its main goals. */
function newsAccent(p:any){
 const body=group(p);
 if(!body&&isDecadeWide(p.mgs||[]))return {style:accentStyle({}),tag:'Decade-wide'};
 const a=eventAccent({body,ocs:body?[]:linkedGroups(p.mgs||[])});
 return {style:accentStyle({body,ocs:body?[]:linkedGroups(p.mgs||[])}),tag:body||linkedGroups(p.mgs||[]).length?a.tag:'Decade community'};
}
/** The heading of a news item: its title, or the first words of its text when it has none. */
const headline=(p:any)=>{if(p.title?.trim())return p.title.trim();const first=(p.body||'').trim().split(/\n|(?<=[.!?])\s/)[0]||'';return first.length>90?first.slice(0,89)+'…':first||'News';};
const hasOwnTitle=(p:any)=>!!p.title?.trim();

export function NewsBoard({uid,name,admin,access}:{uid:string;name:string;admin:boolean;access:MeetingAccess}){
 const [posts,setPosts]=useState<any[]>([]),[draft,setDraft]=useState<any>(null),[selected,setSelected]=useState<any>(null),[filter,setFilter]=useState(''),[error,setError]=useState(''),[saving,setSaving]=useState(false);
 useEffect(()=>{if(!db)return;return onSnapshot(query(collection(db,'posts'),orderBy('createdAt','desc'),limit(51)),s=>setPosts(s.docs.map(d=>({id:d.id,...d.data()}))),e=>setError(friendlyError(e)));},[uid]);
 const current=posts.find(p=>p.id===selected?.id);
 const shown=posts.slice(0,50).filter(p=>!filter||group(p)===filter||(/^wg[1-5]$/.test(filter)&&linkedGroups(p.mgs).includes(Number(filter[2]))));
 async function save(e:React.FormEvent){e.preventDefault();if(!db)return;setSaving(true);setError('');try{const fields={title:draft.title.trim(),body:draft.body.trim(),url:draft.url.trim(),bodyId:draft.bodyId,mgs:draft.mgs||[],wg:/^wg[1-5]$/.test(draft.bodyId)?Number(draft.bodyId[2]):0,attachments:cleanAttachments(draft.attachments),updatedAt:serverTimestamp()};if(draft.id)await updateDoc(doc(db,'posts',draft.id),fields);else await setDoc(doc(collection(db,'posts')),{...fields,author:uid,author_name:name,createdAt:serverTimestamp()});setDraft(null);toast.success(draft.id?'News updated.':'News published.');}catch(e){setError(friendlyError(e));}finally{setSaving(false);}}
 function edit(p:any){setDraft({id:p.id,title:p.title||'',body:p.body,url:p.url||'',bodyId:group(p),mgs:p.mgs||[],attachments:p.attachments||[],saved:(p.attachments||[]).map((a:any)=>a.id)});setSelected(null);}
 async function remove(p:any){if(!confirm('Delete this news item and its comments?'))return;try{await deleteDoc(doc(db!,'posts',p.id));setSelected(null);toast.success('News deleted.');}catch(e){setError(friendlyError(e));}}
 const filters=[['','All news'],...meetingBodies.map(b=>[b.id,shortBody(b.id)])];
 return <section className="news-board">
  <div className="news-toolbar">
   <div className="news-filters" role="group" aria-label="News from">
    {filters.map(([id,label])=><button key={id} type="button" className={'news-filter'+(filter===id?' on':'')} aria-pressed={filter===id} onClick={()=>setFilter(id)}>{label}</button>)}
   </div>
   <button className="btn primary" onClick={()=>setDraft({title:'',body:'',url:'',bodyId:'',mgs:[]})}><Plus size={16}/> Share news</button>
  </div>
  {error&&<p className="error-banner" role="alert">{error}</p>}
  {posts.length>50&&<p className="notice">Showing the latest 50 news items.</p>}
  <div className="news-grid">
   {shown.map((p,i)=>{const a=newsAccent(p),files=(p.attachments||[]).length;return(
    <article className={'news-card'+(i===0&&!filter?' lead':'')} key={p.id} style={a.style}>
     <div className="news-card-top"><span className="news-tag"><i/>{a.tag}</span><time className="micro">{day(p.createdAt)}</time></div>
     <button type="button" className="news-card-main" onClick={()=>setSelected(p)}>
      <h3>{headline(p)}</h3>
      {(()=>{const rest=hasOwnTitle(p)?p.body:headline(p).endsWith('…')?p.body:(p.body||'').slice(headline(p).length).trim();return rest?<p className="news-excerpt">{rest}</p>:null;})()}
     </button>
     <div className="news-card-meta">
      {files>0&&<span><Paperclip size={13}/>{files} {files===1?'file':'files'}</span>}
      {p.url&&<a href={p.url} target="_blank" rel="noopener noreferrer"><ArrowUpRight size={13}/>Source</a>}
      {(p.mgs||[]).length>0&&<span>{isDecadeWide(p.mgs)?'All 15 main goals':`${p.mgs.length} main ${p.mgs.length===1?'goal':'goals'}`}</span>}
     </div>
     <div className="news-card-footer">
      <CreatedBy uid={p.author} verb="Shared by" compact fallback={p.author_name}/>
      <button type="button" className="text-button" onClick={()=>setSelected(p)}><MessageSquare size={14}/> Read and comment <ChevronRight size={14}/></button>
     </div>
    </article>);})}
  </div>
  {!shown.length&&!error&&<div className="glass empty-state"><Newspaper size={28}/><h3>{filter?'No news from this group yet':'Share news from the Decade'}</h3><p>Publish an update, a useful resource or a result. Members can discuss it in the comments.</p></div>}

  <Dialog open={!!draft} onOpenChange={v=>!v&&!saving&&setDraft(null)}><DialogContent className="detail-content news-form"><DialogTitle>{draft?.id?'Edit news':'Share news'}</DialogTitle><DialogDescription>Visible to all members of the platform.</DialogDescription>
   {draft&&<form onSubmit={save}><fieldset disabled={saving}>
    <label>Title<input maxLength={160} required value={draft.title} placeholder="A short, informative title" onChange={e=>setDraft({...draft,title:e.target.value})}/></label>
    <label>Text<textarea required maxLength={3000} rows={7} value={draft.body} onChange={e=>setDraft({...draft,body:e.target.value})}/><small className="micro">{draft.body.length} / 3,000 characters</small></label>
    <div className="field"><label htmlFor="news-body">Shared for</label><select id="news-body" value={draft.bodyId} onChange={e=>setDraft({...draft,bodyId:e.target.value})}><option value="">The whole Decade community</option>{meetingBodies.map(b=><option key={b.id} value={b.id}>{b.label}</option>)}</select></div>
    <GoalPicker label="Contribution to main goals (optional)" value={draft.mgs||[]} onChange={mgs=>setDraft({...draft,mgs})}/>
    <label>Source or related link (optional)<input type="url" maxLength={1000} placeholder="https://" value={draft.url} onChange={e=>setDraft({...draft,url:e.target.value})}/></label>
    {shareBody(access,draft.bodyId)!==null&&<AttachmentPicker value={draft.attachments||[]} saved={draft.saved||[]} onChange={attachments=>setDraft((d:any)=>d&&{...d,attachments})} body={shareBody(access,draft.bodyId)||''}/>}
    {error&&<p className="error-banner" role="alert">{error}</p>}
    <div className="toolbar"><button type="submit" className="btn primary">{saving?'Publishing…':draft.id?'Save changes':'Publish news'}</button><button className="btn" type="button" onClick={()=>setDraft(null)}>Cancel</button></div>
   </fieldset></form>}
  </DialogContent></Dialog>

  <Dialog open={!!current} onOpenChange={v=>!v&&setSelected(null)}><DialogContent className="detail-content news-reader">
   {current&&(()=>{const a=newsAccent(current);return <>
    <header className="news-reader-head" style={a.style}>
     <div className="news-card-top"><span className="news-tag"><i/>{a.tag}</span><time className="micro">{day(current.createdAt)}</time></div>
     <DialogTitle>{headline(current)}</DialogTitle>
     <DialogDescription asChild><div className="news-reader-by"><CreatedBy uid={current.author} verb="Shared by" at={iso(current.createdAt)} fallback={current.author_name}/>
      {(admin||current.author===uid)&&<span className="news-reader-actions"><button type="button" className="text-button" onClick={()=>edit(current)}><Pencil size={13}/> Edit</button><button type="button" className="text-button danger" onClick={()=>remove(current)}><Trash2 size={13}/> Delete</button></span>}
     </div></DialogDescription>
    </header>
    <div className="news-reader-body">
     <p className="news-text">{current.body}</p>
     {current.url&&<a className="btn small news-source" href={current.url} target="_blank" rel="noopener noreferrer"><ArrowUpRight size={14}/> Open the source</a>}
     <AttachmentList items={current.attachments}/>
     {(current.mgs||[]).length>0&&<div className="news-goals"><span className="micro">Contributes to</span><GoalLabels value={current.mgs}/></div>}
    </div>
    <NewsComments postId={current.id} uid={uid} name={name} admin={admin}/>
   </>;})()}
  </DialogContent></Dialog>
 </section>;
}

function NewsComments({postId,uid,name,admin}:{postId:string;uid:string;name:string;admin:boolean}){
 const [items,setItems]=useState<any[]>([]),[text,setText]=useState(''),[editing,setEditing]=useState(''),[saving,setSaving]=useState(false),[error,setError]=useState('');
 const me=usePerson(uid);
 useEffect(()=>{if(!db)return;return onSnapshot(query(collection(db,'posts',postId,'comments'),orderBy('createdAt','desc'),limit(51)),s=>setItems(s.docs.map(d=>({id:d.id,...d.data()}))),e=>setError(friendlyError(e)));},[postId]);
 async function submit(e?:React.FormEvent){e?.preventDefault();if(!db||!text.trim())return;setSaving(true);setError('');try{if(editing)await updateDoc(doc(db,'posts',postId,'comments',editing),{body:text.trim(),updatedAt:serverTimestamp()});else await setDoc(doc(collection(db,'posts',postId,'comments')),{author:uid,author_name:name,body:text.trim(),createdAt:serverTimestamp(),updatedAt:serverTimestamp()});setText('');setEditing('');}catch(e){setError(friendlyError(e));}finally{setSaving(false);}}
 // Oldest first, as in a conversation.
 const list=items.slice(0,50).reverse();
 return <section className="news-comments" aria-label="Comments">
  <h3><MessageSquare size={16}/> Comments{items.length>0&&<em>{items.length>50?'50+':items.length}</em>}</h3>
  {items.length>50&&<p className="notice">Showing the latest 50 comments.</p>}
  {list.length?<ol className="news-thread">{list.map(item=><NewsComment key={item.id} item={item} mine={item.author===uid} canEdit={admin||item.author===uid}
    onEdit={()=>{setEditing(item.id);setText(item.body);}}
    onDelete={async()=>{if(!confirm('Delete this comment?'))return;try{await deleteDoc(doc(db!,'posts',postId,'comments',item.id));}catch(e){setError(friendlyError(e));}}}/>)}</ol>
   :<p className="news-thread-empty">No comment yet. Be the first to react to this news.</p>}
  <form className="news-composer" onSubmit={submit}>
   <MemberAvatar name={name} uid={uid} hasPhoto={me?.hasPhoto} version={me?.updatedAt}/>
   <div className="news-composer-box">
    <textarea aria-label={editing?'Edit your comment':'Write a comment'} placeholder={editing?'Edit your comment':'Write a comment…'} required maxLength={1500} rows={2} value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();void submit();}}}/>
    <div className="news-composer-bar"><span className="micro">{editing?'Editing your comment':'Ctrl + Enter to post'}</span>
     <span>{editing&&<button className="btn small" type="button" onClick={()=>{setEditing('');setText('');}}>Cancel</button>}<button className="btn small primary" type="submit" disabled={saving||!text.trim()}><Send size={13}/> {saving?'Saving…':editing?'Save':'Post'}</button></span>
    </div>
   </div>
  </form>
  {error&&<p className="error-banner" role="alert">{error}</p>}
 </section>;
}

function NewsComment({item,mine,canEdit,onEdit,onDelete}:{item:any;mine:boolean;canEdit:boolean;onEdit:()=>void;onDelete:()=>void}){
 const p=usePerson(item.author),name=p?.name||item.author_name||'A member';
 const at=iso(item.createdAt),edited=iso(item.updatedAt)&&at&&Date.parse(iso(item.updatedAt))-Date.parse(at)>60000;
 return <li className={'news-comment'+(mine?' mine':'')}>
  <MemberAvatar name={name} uid={item.author} hasPhoto={p?.hasPhoto} version={p?.updatedAt}/>
  <div className="news-bubble">
   <div className="news-bubble-head"><strong>{name}</strong><time className="micro">{at?new Date(at).toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'}):''}{edited?' · edited':''}</time></div>
   <p>{item.body}</p>
   {canEdit&&<div className="news-bubble-actions"><button type="button" className="text-button" onClick={onEdit}><Pencil size={12}/> Edit</button><button type="button" className="text-button danger" onClick={onDelete}><Trash2 size={12}/> Delete</button></div>}
  </div>
 </li>;
}
