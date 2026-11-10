import {inventoryModel} from './inventory-model.mjs?v=20261108-day13';
import {createResultCard} from './result-view.mjs?v=20261108-day13';
import {mountGachaDialog} from './details.mjs?v=20261108-day13';
export function mountInventory(root,{store}){
 const doc=root.ownerDocument,rows=new Map();let visible=false;
 const button=doc.createElement('button');button.type='button';button.className='ui-button gacha-inventory-open';button.textContent='카드 보관함';root.querySelector('.gacha-bottom').before(button);
 const modal=mountGachaDialog(root,{titleId:'gacha-inventory-title',onVisible:()=>visible});modal.dialog.classList.add('gacha-collection-dialog');
 modal.content.innerHTML='<div class="gacha-collection-tools"><label>희귀도 <select data-rarity><option value="all">전체</option><option>R2</option><option>R3</option><option>R4</option></select></label><label>정렬 <select data-sort><option value="id">카드 ID</option><option value="count">수량 많은 순</option><option value="rarity">희귀도 높은 순</option></select></label></div><p role="status" aria-live="polite"></p><ol class="gacha-inventory-grid"></ol>';
 const status=modal.content.querySelector('[role=status]'),list=modal.content.querySelector('ol'),rarity=modal.content.querySelector('[data-rarity]'),sort=modal.content.querySelector('[data-sort]');
 const render=()=>{if(!visible||!modal.dialog.open)return;const state=store.snapshot,m=inventoryModel(state.wallet,{rarity:rarity.value,sort:sort.value});
  status.textContent=state.error||m.status==='error'?'저장 오류 · 보관함을 읽을 수 없습니다. 가챠 화면의 저장 복구 안내를 확인하세요.':m.status==='empty'?'아직 획득한 카드가 없습니다.':m.status==='filtered-empty'?'선택한 희귀도의 카드가 없습니다.':`전체 ${m.total}장 · ${m.unique}종 · 현재 ${m.cards.length}종 표시`;
  const items=state.error?[]:m.cards,wanted=new Set(items.map(c=>c.cardId));
  for(const [id,row] of rows)if(!wanted.has(id)){if(row.el.contains(doc.activeElement))rarity.focus({preventScroll:true});row.el.remove();rows.delete(id);}
  for(const [index,item] of items.entries()){
   let row=rows.get(item.cardId);
   if(!row){const el=createResultCard(doc,{...item,index,key:item.cardId,isNew:null}),count=doc.createElement('p'),history=doc.createElement('details'),summary=doc.createElement('summary'),records=doc.createElement('ol');
    summary.textContent='획득 기록 보기';history.append(summary,records);el.append(count,history);row={el,count,records,historyKey:null};rows.set(item.cardId,row);
   }
   row.count.textContent=`보유 ${item.count}장 · 중복 ${item.duplicates}장`;row.el.querySelector('.gacha-result-position').textContent=String(index+1).padStart(2,'0');
   const historyKey=JSON.stringify(item.history);
   if(row.historyKey!==historyKey){row.historyKey=historyKey;row.records.replaceChildren();for(const record of item.history){const li=doc.createElement('li');li.textContent=`${record.source==='exchange'?'교환':'추첨'} · ${record.bannerId} · ${record.requestId} · ${record.index+1}번째`;row.records.append(li);}}
   if(list.children[index]!==row.el)list.insertBefore(row.el,list.children[index]??null);
  }
 };
 const open=opener=>{store.refresh();if(modal.open('카드 보관함',opener??button))render();};
 const click=()=>open(button);button.addEventListener('click',click);rarity.addEventListener('change',render);sort.addEventListener('change',render);const off=store.subscribe(render);
 return {open,setVisible(v){visible=v;if(!v)modal.close(false);},close(){modal.close(false);},destroy(){off();rows.clear();button.removeEventListener('click',click);rarity.removeEventListener('change',render);sort.removeEventListener('change',render);modal.destroy();button.remove();}};
}
