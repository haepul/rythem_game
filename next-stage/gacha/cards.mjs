// Stable draw IDs. Art keys are replaceable presentation tokens, not identities.
export const RARITIES=Object.freeze(['R2','R3','R4']);
export const CARDS=Object.freeze([
 {id:'test-card-001',rarity:'R2',placeholderArtKey:'mint-diamond'},
 {id:'test-card-002',rarity:'R2',placeholderArtKey:'mint-circle'},
 {id:'test-card-003',rarity:'R3',placeholderArtKey:'lilac-diamond'},
 {id:'test-card-004',rarity:'R3',placeholderArtKey:'lilac-circle'},
 {id:'test-card-005',rarity:'R4',placeholderArtKey:'peach-diamond'},
 {id:'test-card-006',rarity:'R4',placeholderArtKey:'peach-circle'}
].map(Object.freeze));
