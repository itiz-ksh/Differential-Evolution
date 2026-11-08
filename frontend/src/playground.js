export const POPULATION=20;
export function landscape(kind,x,y){return kind==='sphere'?x*x+y*y:20+x*x+y*y-10*(Math.cos(2*Math.PI*x)+Math.cos(2*Math.PI*y))}
function random(s){s.rng=(Math.imul(1664525,s.rng)+1013904223)>>>0;return s.rng/4294967296}
const clamp=x=>Math.max(-5,Math.min(5,x));
function point(s,x,y){return {x,y,value:landscape(s.landscape,x,y)}}
export function createSearch(method,seed,kind,mutation=.7,crossover=.7){
 const s={method,landscape:kind,mutation,crossover,rng:seed>>>0,points:[],history:[],evaluations:0,generation:0};
 for(let i=0;i<POPULATION;i++)s.points.push(point(s,random(s)*10-5,random(s)*10-5));
 s.evaluations=POPULATION;s.best=Math.min(...s.points.map(p=>p.value));s.history.push(s.best);return s;
}
export function stepSearch(s){
 const old=s.points; const next=[];
 for(let i=0;i<POPULATION;i++){
  let candidate;
  if(s.method==='de'){
   const indices=[];while(indices.length<3){const n=Math.floor(random(s)*POPULATION);if(n!==i&&!indices.includes(n))indices.push(n)}
   const [a,b,c]=indices.map(n=>old[n]), forced=Math.floor(random(s)*2);
   const x=forced===0||random(s)<s.crossover?clamp(a.x+s.mutation*(b.x-c.x)):old[i].x;
   const y=forced===1||random(s)<s.crossover?clamp(a.y+s.mutation*(b.y-c.y)):old[i].y;
   candidate=point(s,x,y);next.push(candidate.value<=old[i].value?candidate:old[i]);
  }else if(s.method==='random') next.push(point(s,random(s)*10-5,random(s)*10-5));
  else {const p=old[i];candidate=point(s,clamp(p.x+(random(s)*2-1)*.5),clamp(p.y+(random(s)*2-1)*.5));next.push(candidate.value<=p.value?candidate:p)}
 }
 s.points=next;s.evaluations+=POPULATION;s.generation++;s.best=Math.min(s.best,...next.map(p=>p.value));s.history.push(s.best);return s;
}
