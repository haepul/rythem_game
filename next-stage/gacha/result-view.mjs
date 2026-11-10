import {revealTheme} from './reveal-theme.mjs?v=20261108-day13';

// Non-interactive card renderer, reusable by a future inventory view.
export function createResultCard(doc,card){
 const el=doc.createElement('li'),theme=revealTheme(card.rarity);
 el.className='gacha-result-card';el.dataset.resultKey=card.key;el.dataset.rarity=theme.key;
 el.style.setProperty('--result-accent',theme.accent);el.style.setProperty('--result-light',theme.light);
 const part=(tag,cls,text)=>{const node=doc.createElement(tag);node.className=cls;node.textContent=text;el.append(node);return node;};
 part('span','gacha-result-position',String(card.index+1).padStart(2,'0'));
 if(card.isNew===true){const badge=part('span','gacha-result-new','NEW');badge.setAttribute('role','img');badge.setAttribute('aria-label','NEW · 처음 획득');}
 const symbol=part('span','gacha-result-symbol','◇');symbol.setAttribute('aria-hidden','true');
 part('strong','gacha-result-rarity',card.rarity??'희귀도 확인 불가');
 part('p','gacha-result-id',card.cardId??'카드 ID 확인 불가');
 return el;
}

export function createResultView(doc){
 const element=doc.createElement('section');element.className='gacha-results';
 const banner=doc.createElement('p');banner.className='gacha-results-banner';
 const live=doc.createElement('p');live.className='gacha-results-announcement';live.setAttribute('role','status');live.setAttribute('aria-live','polite');live.setAttribute('aria-atomic','true');
 const list=doc.createElement('ol');list.className='gacha-result-grid';list.setAttribute('aria-label','추첨 순서대로 획득한 카드');
 const unknown=doc.createElement('p');unknown.className='gacha-result-unknown';unknown.textContent='획득 이력을 확인할 수 없어 NEW 여부를 표시하지 않습니다.';
 const summary=doc.createElement('dl');summary.className='gacha-result-summary';
 const values={};for(const [key,label] of [['cost','사용 크리스탈'],['after','추첨 직후 잔액'],['current','현재 잔액']]){const item=doc.createElement('div'),dt=doc.createElement('dt'),dd=doc.createElement('dd');dt.textContent=label;item.append(dt,dd);summary.append(item);values[key]=dd;}
 element.append(banner,live,list,unknown,summary);let model=null,currentText=null;
 const amount=n=>Number.isSafeInteger(n)&&n>=0?n.toLocaleString('ko-KR'):'확인 불가';
 return {element,
  render(next,{bannerName,balance}={}){
   // Store subscriptions update only the current balance, preserving card DOM,
   // focus, scroll and the historical NEW snapshot of the open result.
   if(model!==next){model=next;element.dataset.count=String(next.count);
    banner.textContent=`${bannerName??next.bannerId} · ${next.count}회 결과`;
    list.replaceChildren(...next.cards.map(card=>createResultCard(doc,card)));
    unknown.hidden=next.newStatus==='known';
    values.cost.textContent=amount(next.cost);values.after.textContent=amount(next.balanceAfter);
    live.textContent=`${next.count}장의 카드 결과가 저장되었습니다.${next.newStatus==='known'?` 처음 획득 ${next.cards.filter(c=>c.isNew).length}장.`:' 획득 이력 확인 불가.'}`;
   }
   const value=amount(balance);if(currentText!==value){currentText=value;values.current.textContent=value;}
  }
 };
}
