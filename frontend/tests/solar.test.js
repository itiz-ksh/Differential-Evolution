import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {power,createSolarSearch,stepSolarSearch} from '../src/solar.js';
test('solar curve is bounded and partial shade has multiple peaks',()=>{assert.equal(power(0,false),0);assert.equal(power(40,true),0);let peaks=0;for(let v=.1;v<39.9;v+=.1)if(power(v,true)>power(v-.1,true)&&power(v,true)>power(v+.1,true))peaks++;assert.ok(peaks>=2)});
test('DE retains its best power and stays inside voltage limits reproducibly',()=>{const a=createSolarSearch(true,42),b=createSolarSearch(true,42);for(let i=0;i<20;i++){stepSolarSearch(a);stepSolarSearch(b)}assert.deepEqual(a,b);assert.ok(a.points.every(p=>p.voltage>=0&&p.voltage<=40));assert.ok(a.history.every((v,i,h)=>!i||v>=h[i-1]));assert.equal(a.evaluations,252)});
