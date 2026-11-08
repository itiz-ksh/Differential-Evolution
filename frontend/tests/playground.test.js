import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {createSearch, stepSearch, landscape} from '../src/playground.js';
test('searches are reproducible, bounded and use equal budgets', () => {
  for (const method of ['de','random','hill']) {
    const a=createSearch(method,42,'rastrigin'), b=createSearch(method,42,'rastrigin');
    for(let i=0;i<8;i++){stepSearch(a);stepSearch(b)}
    assert.deepEqual(a,b); assert.equal(a.evaluations,180);
    assert.ok(a.points.every(p=>p.x>=-5&&p.x<=5&&p.y>=-5&&p.y<=5));
    assert.ok(a.history.every((v,i,h)=>!i||v<=h[i-1]));
  }
});
test('landscapes have a minimum at the origin',()=>{assert.equal(landscape('rastrigin',0,0),0);assert.equal(landscape('sphere',0,0),0)});
