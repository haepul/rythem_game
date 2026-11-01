import {CARDS,RARITIES} from './cards.mjs?v=20261101-day7';

export const BASIS_POINTS=10000;
export const TEST_DRAW_CONFIG=Object.freeze({
 schemaVersion:1,version:'project-test-v1',guarantee:'none',
 pools:Object.freeze([
  {rarity:'R2',weightBps:8000,cardIds:['test-card-001','test-card-002']},
  {rarity:'R3',weightBps:1500,cardIds:['test-card-003','test-card-004']},
  {rarity:'R4',weightBps:500,cardIds:['test-card-005','test-card-006']}
 ].map(p=>Object.freeze({...p,cardIds:Object.freeze(p.cardIds)})))
});
export const DRAW_CONFIGS=Object.freeze({[TEST_DRAW_CONFIG.version]:TEST_DRAW_CONFIG});
export const BANNER_DRAW_CONFIG_IDS=Object.freeze(Object.fromEntries(
 ['demo-mint','demo-lilac','demo-peach'].map(id=>[id,TEST_DRAW_CONFIG.version])));
export class DrawConfigError extends Error{constructor(code){super(code);this.name='DrawConfigError';this.code=code;}}
const fail=code=>{throw new DrawConfigError(code);};
const text=value=>typeof value==='string'&&value.trim().length>0;
const fields=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&
 Object.keys(value).sort().join(',')===[...keys].sort().join(',');

// Shared by sampling and disclosure. Strict shape rejects unimplemented rules.
export function validateDrawConfig(config,cards=CARDS){
 if(!fields(config,['schemaVersion','version','guarantee','pools']))fail('invalid-config');
 if(config.schemaVersion!==1||!text(config.version))fail('unsupported-version');
 if(config.guarantee!=='none')fail('unsupported-guarantee');
 if(!Array.isArray(cards)||cards.length===0)fail('empty-catalog');
 const catalog=new Map();
 for(const card of cards){
  if(!fields(card,['id','rarity','placeholderArtKey'])||!text(card.id)||!text(card.placeholderArtKey)||!RARITIES.includes(card.rarity))fail('invalid-card');
  if(catalog.has(card.id))fail('duplicate-card-id');catalog.set(card.id,card);
 }
 if(!Array.isArray(config.pools)||config.pools.length!==RARITIES.length)fail('invalid-pools');
 const rarities=new Set(),ids=new Set();let total=0;
 for(const pool of config.pools){
  if(!fields(pool,['rarity','weightBps','cardIds'])||!RARITIES.includes(pool.rarity)||rarities.has(pool.rarity))fail('invalid-rarity');
  rarities.add(pool.rarity);
  if(!Number.isSafeInteger(pool.weightBps)||pool.weightBps<0||pool.weightBps>BASIS_POINTS)fail('invalid-weight');
  total+=pool.weightBps;
  if(!Array.isArray(pool.cardIds)||(pool.weightBps>0&&pool.cardIds.length===0))fail('empty-pool');
  for(const id of pool.cardIds){
   if(!text(id)||!catalog.has(id))fail('missing-card');
   if(ids.has(id))fail('duplicate-pool-card');ids.add(id);
   if(catalog.get(id).rarity!==pool.rarity)fail('rarity-mismatch');
  }
 }
 if(total!==BASIS_POINTS)fail('invalid-total');
 return true;
}

// Per-card probability is an exact rational number of basis points; no rounding
// is fed back into the engine. Cards within a rarity are always uniform.
export function drawProbabilities(config,cards=CARDS){
 validateDrawConfig(config,cards);
 return {version:config.version,guarantee:config.guarantee,
  rarities:config.pools.map(p=>({rarity:p.rarity,weightBps:p.weightBps})),
  cards:config.pools.flatMap(p=>p.cardIds.map(cardId=>({cardId,rarity:p.rarity,numeratorBps:p.weightBps,denominator:p.cardIds.length})))
 };
}
