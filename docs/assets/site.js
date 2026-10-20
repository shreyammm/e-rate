'use strict';
const pick=id=>document.getElementById(id);
const AREAS={scope:'E-Rate scope',funding:'Funding and discounts',accountability:'Accountability',evaluation:'Educational outcomes',screens:'Screens and parental choice',cipa:'CIPA and internet safety',consultants:'Consultants',administration:'Administration'};
const POSITIONS=['support','oppose','conditional_or_amend','alternative_proposal','discussion_no_position','unclear','not_addressed'];
let codebook=[],results={provisions:[]};
function node(tag,cls,value){const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=String(value);return e;}
function render(){
  const area=pick('area').value,term=pick('search').value.trim().toLocaleLowerCase(),stance=pick('position').value;
  const container=pick('proposals');container.replaceChildren();
  const map=new Map(results.provisions.map(p=>[p.id,p]));
  const visible=codebook.filter(p=>(area==='all'||p.category===area)
    &&(!term||(p.label+' '+p.policy_option+' '+p.category).toLocaleLowerCase().includes(term))
    &&(stance==='all'||((map.get(p.id)?.counts||{})[stance]||0)>0));
  pick('result-count').textContent=visible.length+' of '+codebook.length+' policy questions';
  if(!visible.length){container.append(node('div','empty','No proposals match the current filters.'));return;}
  for(const p of visible){
    const article=node('article','proposal');
    const top=node('div','head'),left=node('div');
    left.append(node('div','meta',(AREAS[p.category]||p.category)+' · Notice '+p.notice_paragraph_range+' · '+p.notice_status.replaceAll('_',' ')),
      node('h3','',p.label),node('p','question',p.policy_option));
    const record=map.get(p.id),count=Number(record?.adjudicated_filing_count||0);
    top.append(left,node('span','review',count?'Reviewed: '+count+' filing/provision pairs':'Review pending'));article.append(top);
    const detail=node('div','detail');
    if(count){
      const badges=node('div','badges');
      for(const key of POSITIONS){const val=Number(record.counts?.[key]||0);if(val)badges.append(node('span','badge',key.replaceAll('_',' ')+': '+val));}
      detail.append(badges);
      const note=node('p','results-note','Counts include only individually reviewed filing/provision pairs. They are NOT percentages of all commenters.');
      detail.append(note);
      const nArguments=Number(record.reviewed_argument_count||0);
      if(nArguments){
        const group=node('div','argument-analysis');
        group.append(node('h4','','Arguments found in reviewed filings'),
          node('p','results-note',nArguments+' manually validated argument rows. These are multiple possible claims per filing, not additional commenters.'));
        const argumentsList=node('div','badges');
        for(const [kind,n] of Object.entries(record.reviewed_argument_types||{})){
          if(Number(n)>0)argumentsList.append(node('span','badge',kind.replaceAll('_',' ')+': '+n));
        }
        group.append(argumentsList);
        detail.append(group);
      }
      const examples=record.evidence||[];
      if(examples.length){
        const list=node('ul','examples');
        for(const example of examples){
          const li=node('li'),link=node('a','',example.position.replaceAll('_',' ')+' — FCC filing '+example.filing_id);
          const u=String(example.source_url||'');
          if(/^https:\/\/www\.fcc\.gov\/ecfs\//.test(u)){link.href=u;link.target='_blank';link.rel='noopener noreferrer';li.append(link);}
          if(example.quote){li.append(node('span','',': '+example.quote));}
          list.append(li);
        }
        detail.append(list);
      }
    }else{
      detail.append(node('p','results-note','No evidence-validated position counts published for this proposal yet. Keyword matches alone are not classified as support or opposition.'));
    }
    article.append(detail);container.append(article);
  }
}
async function main(){
  try{
    const [bookRes,resRes]=await Promise.all([fetch('./data/provisions.json',{cache:'no-store'}),fetch('./data/public_results.json',{cache:'no-store'})]);
    if(!bookRes.ok||!resRes.ok)throw new Error('Research files are unavailable');
    const book=await bookRes.json();results=await resRes.json();codebook=book.provisions||[];
    const count=Number(results.reviewed_filing_provision_pairs||0);
    pick('status').textContent=count
      ?'Early research preview · '+count+' human-reviewed filing/provision pairs. Not a census or public-opinion estimate.'
      :'Research preview · Methodology and rulemaking questions available; validated position results are not yet published.';
    const area=pick('area');
    [...new Set(codebook.map(p=>p.category))].sort().forEach(key=>{const o=node('option','',AREAS[key]||key);o.value=key;area.append(o);});
    for(const id of ['area','search','position'])pick(id).addEventListener(id==='search'?'input':'change',render);
    render();
  }catch(e){pick('status').textContent='Research preview: unable to load the current data files.';
    pick('proposals').append(node('p','empty','Data could not be loaded. View the open-source methods and FCC notice using the links below.'));}
}
document.addEventListener('DOMContentLoaded',main);