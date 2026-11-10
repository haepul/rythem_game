// Immutable project-only free simulation policy. Never edit a published version.
const freeze=o=>{Object.values(o).forEach(v=>{if(v&&typeof v==='object')freeze(v);});return Object.freeze(o);};
export const REWARD_VERSION='free-rewards-v1';
// Legacy receipts always receive the first policy, even after a future default changes.
export const LEGACY_REWARD_VERSION='free-rewards-v1';
export const REWARD_RULES=freeze({'free-rewards-v1':{version:'free-rewards-v1',stickersPerCard:1,progressPerCard:1,threshold:10,bonusStickers:2,exchangeCost:10,banners:['demo-mint','demo-lilac','demo-peach'],cards:[{id:'test-card-001',rarity:'R2'},{id:'test-card-002',rarity:'R2'},{id:'test-card-003',rarity:'R3'},{id:'test-card-004',rarity:'R3'},{id:'test-card-005',rarity:'R4'},{id:'test-card-006',rarity:'R4'}]}});
export function rewardRule(version=REWARD_VERSION){if(!Object.hasOwn(REWARD_RULES,version))throw Error('unsupported-reward-version');return REWARD_RULES[version];}
