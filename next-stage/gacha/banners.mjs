// Display-only projection of the DAY 1 BannerDefinition. No draw rules yet.
const art = name => new URL(`./assets/${name}.svg`, import.meta.url).href;
export const BANNER_ART = Object.freeze(Object.fromEntries(['mint','lilac','peach'].map(key => [key,
 Object.freeze({heroSrc:art(key),thumbnailSrc:art(key)})])));
export const BANNER_THEMES = Object.freeze({mint:'mint',lilac:'lilac',peach:'peach'});
export const BANNERS = Object.freeze([
 {id:'demo-mint',title:'민트 스테이지',subtitle:'맑은 민트빛과 겹쳐진 마름모. 가볍게 펼쳐지는 새로운 무대의 색을 살펴보세요.',previewLabel:'디자인 미리보기',artKey:'mint',themeKey:'mint'},
 {id:'demo-lilac',title:'라일락 스테이지',subtitle:'잔잔한 라벤더빛과 부드러운 원의 리듬. 서로 다른 빛이 만나는 구성을 살펴보세요.',previewLabel:'디자인 미리보기',artKey:'lilac',themeKey:'lilac'},
 {id:'demo-peach',title:'피치 스테이지',subtitle:'연한 살구빛과 경쾌한 삼각형. 따뜻한 색으로 채운 기하학 무대를 살펴보세요.',previewLabel:'디자인 미리보기',artKey:'peach',themeKey:'peach'}
].map(Object.freeze));
export function validateBanners(input, assets=BANNER_ART){
 const banners=[],errors=[],seen=new Set();
 if(!Array.isArray(input))return {banners,errors:['배너 목록은 배열이어야 합니다.']};
 for(const item of input){
  if(!item||['id','title','subtitle','previewLabel','artKey','themeKey'].some(key=>typeof item[key]!=='string'||!item[key].trim())){errors.push('필수 배너 표시 데이터가 비어 있습니다.');continue;}
  if(seen.has(item.id)){errors.push(`중복 배너 ID: ${item.id}`);continue;}seen.add(item.id);
  if(!Object.hasOwn(BANNER_THEMES,item.themeKey)){errors.push(`알 수 없는 배너 테마: ${item.id}`);continue;}
  const asset=assets[item.artKey];
  if(!asset?.heroSrc||!asset?.thumbnailSrc)errors.push(`배너 자산 누락: ${item.id} / ${item.artKey}`);
  banners.push(Object.freeze({...item}));
 }
 if(!banners.length)errors.push('표시할 배너가 없습니다.');
 return {banners:Object.freeze(banners),errors};
}
