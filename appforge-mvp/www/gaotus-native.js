(()=>{
  'use strict';
  const hasAndroid=()=>typeof window.GaotusNativeAndroid!=='undefined';
  const hasIOS=()=>!!window.webkit?.messageHandlers?.gaotusNative;
  const postIOS=(action,payload={})=>{
    if(!hasIOS())return false;
    window.webkit.messageHandlers.gaotusNative.postMessage({action,payload});
    return true;
  };
  const parse=(value,fallback={})=>{
    try{return typeof value==='object'?value:JSON.parse(value)}catch{return fallback}
  };
  const androidResult=(value,action)=>parse(value,{ok:false,platform:'android',action,error:'invalid_native_response'});

  const Native={
    version:'0.1.2',
    platform:()=>hasAndroid()?'android':hasIOS()?'ios':'web',
    available:()=>hasAndroid()||hasIOS(),
    async ping(){
      if(hasAndroid())return androidResult(window.GaotusNativeAndroid.ping(),'ping');
      if(hasIOS()){postIOS('ping');return{ok:true,platform:'ios'}}
      return{ok:true,platform:'web'};
    },
    async deviceInfo(){
      if(hasAndroid())return androidResult(window.GaotusNativeAndroid.deviceInfo(),'deviceInfo');
      if(hasIOS()){postIOS('deviceInfo');return{ok:true,platform:'ios'}}
      return{ok:true,platform:'web',userAgent:navigator.userAgent};
    },
    async share(options={}){
      const payload={title:String(options.title||''),text:String(options.text||''),url:String(options.url||location.href)};
      if(hasAndroid())return androidResult(window.GaotusNativeAndroid.share(JSON.stringify(payload)),'share');
      if(postIOS('share',payload))return{ok:true,platform:'ios'};
      if(navigator.share){await navigator.share(payload);return{ok:true,platform:'web'}}
      throw new Error('share unavailable');
    },
    async haptic(type='medium'){
      if(hasAndroid())return androidResult(window.GaotusNativeAndroid.haptic(type),'haptic');
      if(postIOS('haptic',{type}))return{ok:true,platform:'ios'};
      navigator.vibrate?.(45);return{ok:true,platform:'web'};
    },
    async openExternal(url){
      url=String(url||'');
      if(!/^https?:\/\//i.test(url))throw new Error('http/https only');
      if(hasAndroid())return androidResult(window.GaotusNativeAndroid.openExternal(url),'openExternal');
      if(postIOS('openExternal',{url}))return{ok:true,platform:'ios'};
      window.open(url,'_blank','noopener');return{ok:true,platform:'web'};
    },
    camera:{
      async open(){
        if(hasAndroid())return androidResult(window.GaotusNativeAndroid.openCamera(),'openCamera');
        if(postIOS('openCamera'))return{ok:true,platform:'ios'};
        const input=document.createElement('input');input.type='file';input.accept='image/*';input.capture='environment';input.click();
        return{ok:true,platform:'web'};
      }
    },
    location:{
      current(options={}){
        return new Promise((resolve,reject)=>navigator.geolocation?navigator.geolocation.getCurrentPosition(
          position=>resolve({ok:true,platform:Native.platform(),latitude:position.coords.latitude,longitude:position.coords.longitude,accuracy:position.coords.accuracy}),
          reject,
          {enableHighAccuracy:true,timeout:options.timeout||10000}
        ):reject(new Error('geolocation unavailable')));
      }
    },
    toast(message){
      if(hasAndroid())return androidResult(window.GaotusNativeAndroid.toast(String(message)),'toast').ok===true;
      return postIOS('toast',{message:String(message)});
    }
  };

  Object.defineProperty(window,'GaotusNative',{value:Native});
  window.dispatchEvent(new CustomEvent('gaotusnative:ready',{detail:{platform:Native.platform()}}));
})();
