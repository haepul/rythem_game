import {CARDS} from './cards.mjs?v=20261101-day7';
import {BASIS_POINTS,validateDrawConfig} from './draw-config.mjs?v=20261101-day7';

export class DrawRandomError extends Error{constructor(){super('RNG must return a finite number in [0, 1).');this.name='DrawRandomError';}}
function random(rng){const value=rng();if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>=1)throw new DrawRandomError();return value;}

// Pure given the injected RNG sequence. No DOM, wallet, persistence or cost.
// All validation happens before RNG use. A failure throws; no partial success.
export function drawCards(config,count,{cards=CARDS,rng=Math.random}={}){
 if(count!==1&&count!==10)throw new RangeError('Only 1 or 10 draws are supported.');
 if(typeof rng!=='function')throw new TypeError('RNG must be a function.');
 validateDrawConfig(config,cards);
 // Snapshot before invoking caller-owned RNG, so it cannot change probabilities
 // partway through the batch. No caller input is mutated.
 const pools=config.pools.map(p=>({...p,cardIds:[...p.cardIds]}));
 const {version:configVersion,schemaVersion}=config,results=[];
 for(let i=0;i<count;i++){
  const rarityRoll=random(rng);let end=0,chosen=null;
  for(const pool of pools){end+=pool.weightBps;
   // [start,end); comparing normalized bounds avoids a multiplied roll rounding
   // onto the next interval. Zero-weight intervals can never be selected.
   if(pool.weightBps>0&&rarityRoll<end/BASIS_POINTS){chosen=pool;break;}
  }
  if(!chosen)throw new RangeError('No weighted interval matched.');
  const cardRoll=random(rng),index=Math.floor(cardRoll*chosen.cardIds.length);
  if(index>=chosen.cardIds.length)throw new RangeError('No card interval matched.');
  results.push({cardId:chosen.cardIds[index],rarity:chosen.rarity,configVersion,schemaVersion});
 }
 return results;
}
