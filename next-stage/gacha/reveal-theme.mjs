// Original project presentation tokens; not official game rarity specifications.
export const REVEAL_TIMING=Object.freeze({card:380});
const themes=Object.freeze({
 R2:Object.freeze({key:'R2',border:'single',accent:'#30bda6',light:'#d7fff4',particles:2}),
 R3:Object.freeze({key:'R3',border:'double',accent:'#bd882b',light:'#fff0c1',particles:4}),
 R4:Object.freeze({key:'R4',border:'prism',accent:'#ab81d9',light:'#eee1ff',particles:6})
});
const neutral=Object.freeze({key:'neutral',border:'dashed',accent:'#7b8394',light:'#edf0f5',particles:0});
export const revealTheme=rarity=>Object.hasOwn(themes,rarity)?themes[rarity]:neutral;
