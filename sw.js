const CACHE_NAME='prouve-spatial-v052-appshell-v3';
const APP_SHELL=['./index.html','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png'];
const LEAFLET_ASSETS=[
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
];
const GEOSPATIAL_ASSETS=[
  'https://cdn.jsdelivr.net/npm/geotiff@3.0.5/dist-browser/geotiff.js',
  'https://cdn.jsdelivr.net/npm/proj4@2.23.0/dist/proj4.js'
];
self.addEventListener('install',event=>{
  event.waitUntil((async()=>{const cache=await caches.open(CACHE_NAME);await cache.addAll(APP_SHELL);await self.skipWaiting();})());
});
self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{const keys=await caches.keys();await Promise.all(keys.filter(k=>k.startsWith('prouve-spatial-')&&k!==CACHE_NAME).map(k=>caches.delete(k)));await self.clients.claim();})());
});
self.addEventListener('fetch',event=>{
  const req=event.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin==='https://unpkg.com'&&LEAFLET_ASSETS.includes(req.url)){
    event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);const hit=await cache.match(req);if(hit)return hit;try{const res=await fetch(req);if(res.ok||res.type==='opaque')await cache.put(req,res.clone());return res;}catch(e){return new Response('Leaflet library is not cached on this device. Connect once while online, then retry offline.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}})());return;
  }
  if(url.origin==='https://cdn.jsdelivr.net'&&GEOSPATIAL_ASSETS.includes(req.url)){
    event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);const hit=await cache.match(req);if(hit)return hit;try{const res=await fetch(req);if(res.ok||res.type==='opaque')await cache.put(req,res.clone());return res;}catch(e){return hit||new Response('เครื่องมืออ่าน GeoTIFF ยังไม่ถูกเก็บไว้ในอุปกรณ์ กรุณาเชื่อมต่ออินเทอร์เน็ตและเปิดเมนูเตรียมภาพอย่างน้อยหนึ่งครั้ง',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}})());return;
  }
  if(url.origin!==self.location.origin)return;
  if(req.mode==='navigate'){
    event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);try{const res=await fetch(req);if(res.ok)cache.put('./index.html',res.clone());return res;}catch(e){return (await cache.match('./index.html'))||new Response('ยังไม่มีหน้าแอปในอุปกรณ์ กรุณาเชื่อมต่ออินเทอร์เน็ตและเปิดแอปก่อนใช้งานออฟไลน์',{status:503,headers:{'Content-Type':'text/html; charset=utf-8'}});}})());return;
  }
  event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);const hit=await cache.match(req);if(hit)return hit;try{const res=await fetch(req);if(res.ok)cache.put(req,res.clone());return res;}catch(e){return hit||Response.error();}})());
});
