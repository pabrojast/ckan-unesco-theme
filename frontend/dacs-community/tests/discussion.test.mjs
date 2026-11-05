import test from 'node:test';
import assert from 'node:assert/strict';
import {mentionQuery,mentionSuggestions,activeMentions,splitMentions,threadsFrom,timeAgo} from '../lib/discussion.ts';
const people=[{id:'a',name:'Ingrid Halvorsen'},{id:'b',name:'Lucía Mamani'},{id:'c',name:'Omar Haddad'},{id:'me',name:'Alexandre Germouty'}];
test('the @query before the caret is detected only at a word start',()=>{assert.deepEqual(mentionQuery('Hello @Luc'),{query:'Luc',start:6});assert.deepEqual(mentionQuery('@'),{query:'',start:0});assert.equal(mentionQuery('mail@example'),null);assert.equal(mentionQuery('Hello @a b c d e'),null);assert.equal(mentionQuery('line\n'),null);});
test('suggestions ignore accents, put first-name matches first and exclude the author',()=>{assert.deepEqual(mentionSuggestions(people,'luci','me').map(p=>p.id),['b']);assert.deepEqual(mentionSuggestions(people,'had','me').map(p=>p.id),['c']);assert.equal(mentionSuggestions(people,'','me').some(p=>p.id==='me'),false);});
test('only tags still present in the text are kept, without duplicates',()=>{const tagged=[{id:'a',name:'Ingrid Halvorsen'},{id:'b',name:'Lucía Mamani'},{id:'a',name:'Ingrid Halvorsen'}];assert.deepEqual(activeMentions('Thanks @Ingrid Halvorsen, see the draft.',tagged),['a']);});
test('mentions are split out for display, longest names first',()=>{const parts=splitMentions('Ask @Omar Haddad and @Omar.',['Omar Haddad']);assert.deepEqual(parts,[{text:'Ask ',mention:false},{text:'@Omar Haddad',mention:true},{text:' and @Omar.',mention:false}]);});
test('topics are newest first, replies oldest first, empty removed topics hidden',()=>{const m=(id,parent,createdAt,deleted=false)=>({id,parent,createdAt,deleted,space:'wg1',author:'a',author_name:'A',body:'x',mentions:[],updatedAt:createdAt});const t=threadsFrom([m('t1','', '2026-10-01'),m('t2','','2026-10-03'),m('r2','t1','2026-10-05'),m('r1','t1','2026-10-04'),m('t3','','2026-10-06',true),m('orphan','gone','2026-10-02')]);assert.deepEqual(t.map(x=>x.topic.id),['t2','t1']);assert.deepEqual(t[1].replies.map(r=>r.id),['r1','r2']);});

test('relative times use the right unit', () => {
  const now = Date.parse('2026-10-10T12:00:00Z'), at = (min) => new Date(now - min * 60000).toISOString();
  assert.equal(timeAgo(at(0.2), now), 'just now');
  assert.equal(timeAgo(at(45), now), '45 minutes ago');
  assert.equal(timeAgo(at(120), now), '2 hours ago');
  assert.equal(timeAgo(at(26 * 60), now), 'yesterday');
  assert.equal(timeAgo(at(3 * 24 * 60), now), '3 days ago');
  assert.equal(timeAgo(at(30 * 24 * 60), now), '10 Sept 2026');
});
