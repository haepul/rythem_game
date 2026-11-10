import {CARDS} from './cards.mjs?v=20261108-day13';
import {DRAW_COSTS} from './wallet-config.mjs?v=20261108-day13';
import {DRAW_CONFIGS,BANNER_DRAW_CONFIG_IDS,drawProbabilities} from './draw-config.mjs?v=20261108-day13';

export const rarityLabel=rarity=>`${rarity} · ${'★'.repeat(Number(rarity.slice(1)))} 임시 카드`;
export const probabilityLabel=(numeratorBps,denominator=1)=>{
 const percent=numeratorBps/(denominator*100);
 return Number.isInteger(percent*10000)?`${percent}%`:`약 ${percent.toFixed(4)}%`;
};
// Selected banner -> shared validated configuration -> disclosure, never a
// separately maintained probability table. Cost policy is independently versioned.
export function bannerDetails(id,banners,{configs=DRAW_CONFIGS,bindings=BANNER_DRAW_CONFIG_IDS,cards=CARDS}={}){
 const banner=banners.find(item=>item.id===id);
 if(!banner)return null;
 const base={title:banner.title,description:banner.subtitle,status:'unset',rates:null,
  rarity:'희귀도 안내 준비 중 · 실제 등급과 대상 목록은 아직 설정되지 않았습니다.',
  probability:'제공 확률 미설정',rules:'추첨 비용 미설정 · 추첨 실행 준비 중 · 무료 스티커 교환 규칙은 배너의 보너스 안내에서 확인하세요.'};
 try{
  if(!Object.hasOwn(bindings,id)||bindings[id]===null)return base;
  const version=bindings[id];if(!Object.hasOwn(configs,version))throw new Error('missing-config');
  const rates=drawProbabilities(configs[version],cards);
  const sharing=banners.filter(b=>Object.hasOwn(bindings,b.id)&&bindings[b.id]===version).map(b=>b.title);
  return {...base,status:'configured',rates,rarity:'R2 / R3 / R4 · 희귀도별 임시 카드 풀',
   probability:`프로젝트 테스트 규칙 v1 · ${rates.version} · 프세카 공식 확률이 아닙니다.`,
   rules:`10회는 독립 추첨 10번 · 10회 보장 없음 · 프로젝트 테스트 비용: 1회 ${DRAW_COSTS[1]} / 10회 ${DRAW_COSTS[10]} 크리스탈 · 무료 시뮬레이션 · 무료 스티커 교환 규칙은 배너의 보너스 안내에서 확인하세요.`,
   shared:`${sharing.join(' · ')}${sharing.length>1?' 배너는 같은':' 배너의'} 테스트 풀을 사용합니다. 실제 캐릭터 정보는 포함하지 않습니다.`};
 }catch{return {...base,status:'invalid',probability:'확률 설정 오류 · 제공 확률을 표시할 수 없습니다. 설정을 확인해 주세요.'};}
}

export function renderBannerDetails(content,data){
 const doc=content.ownerDocument;content.replaceChildren();
 content.tabIndex=0;content.setAttribute('role','region');content.setAttribute('aria-label','배너 상세 안내 내용');
 for(const text of [data.description,data.probability,data.rarity,data.shared,data.rules].filter(Boolean)){
  const p=doc.createElement('p');p.textContent=text;content.append(p);
 }
 if(!data.rates)return;
 const host=doc.createElement('section');host.className='gacha-probabilities';
 const table=(caption,headers,rows)=>{
  const el=doc.createElement('table'),cap=doc.createElement('caption'),head=doc.createElement('thead'),body=doc.createElement('tbody'),tr=doc.createElement('tr');
  cap.textContent=caption;
  for(const text of headers){const th=doc.createElement('th');th.scope='col';th.textContent=text;tr.append(th);}head.append(tr);
  for(const row of rows){const tr=doc.createElement('tr');row.forEach((text,i)=>{const cell=doc.createElement(i===0?'th':'td');if(i===0)cell.scope='row';cell.textContent=text;tr.append(cell);});body.append(tr);}
  el.append(cap,head,body);host.append(el);
 };
 table('희귀도별 제공 확률',['희귀도','확률'],data.rates.rarities.map(p=>[rarityLabel(p.rarity),probabilityLabel(p.weightBps)]));
 table('카드별 제공 확률 · 같은 희귀도 내 균등',['임시 카드 ID','희귀도','확률'],data.rates.cards.map(p=>[p.cardId,rarityLabel(p.rarity),probabilityLabel(p.numeratorBps,p.denominator)]));
 content.append(host);
}

// Native dialog supplies focus containment/inert background. Leaving the screen
// deliberately discards the opener so a delayed close event cannot steal focus.
export function mountGachaDialog(root,{titleId='gacha-detail-title',onVisible=()=>true,onRequestClose=()=>true}={}){
 const dialog=root.ownerDocument.createElement('dialog');
 dialog.className='ui-modal gacha-dialog';dialog.setAttribute('aria-labelledby',titleId);
 dialog.innerHTML=`<header><p class="eyebrow">RHYTHM STAGE / INFORMATION</p><h2 id="${titleId}"></h2></header><div class="gacha-dialog-content"></div><button type="button" class="ui-button gacha-dialog-close">닫기</button>`;
 root.append(dialog);let opener=null;
 const close=(restore=true)=>{if(!restore)opener=null;if(dialog.open)dialog.close();};
 const closed=()=>{if(dialog.open)return;const target=opener;opener=null;if(onVisible()&&target?.isConnected)target.focus({preventScroll:true});};
 const cancel=e=>{e.preventDefault();if(onRequestClose())close();};
 const keydown=e=>{if(e.key!=='Tab')return;
  const targets=[...dialog.querySelectorAll('button:not(:disabled),[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])')].filter(el=>el.getClientRects().length);
  const first=targets[0],last=targets.at(-1),active=root.ownerDocument.activeElement;
  if((e.shiftKey&&active===first)||(!e.shiftKey&&active===last)){e.preventDefault();(e.shiftKey?last:first)?.focus();}
 };
 const button=dialog.querySelector('button');const click=()=>{if(onRequestClose())close();};
 button.addEventListener('click',click);dialog.addEventListener('cancel',cancel);dialog.addEventListener('close',closed);dialog.addEventListener('keydown',keydown);
 return {dialog,content:dialog.querySelector('.gacha-dialog-content'),
  open(title,target){if(!onVisible()||root.ownerDocument.querySelector('dialog[open]'))return false;
   dialog.querySelector('h2').textContent=title;opener=target;dialog.showModal();button.focus();return true;},
  close,destroy(){close(false);dialog.removeEventListener('cancel',cancel);dialog.removeEventListener('close',closed);dialog.removeEventListener('keydown',keydown);button.removeEventListener('click',click);dialog.remove();}
 };
}
