function log_notif_reception(t){fetch("/1-on-1/push-notif/received/",{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},credentials:"include",body:JSON.stringify({status_code:t})}).then(function(t){if(!t.ok)throw new Error("Bad status code from server.")})}self.addEventListener("fetch",function(t){}),self.addEventListener("push",function(t){var n=t.data.json();log_notif_reception("1");const e=self.registration.showNotification(n.title,{body:n.body,icon:"/static/img/og_image.png",badge:"/static/img/50.png",vibrate:[500,110,500,110,450,110,200,110,170,40,450,110,200,110,170,40,500],tag:n.tag,renotify:!0,silent:!1,requireInteraction:!0,timestamp:n.time});t.waitUntil(e)}),self.addEventListener("notificationclick",function(t){t.notification.close();const n=new URL("/1-on-1/friends/",self.location.origin).href,e=clients.matchAll({type:"window",includeUncontrolled:!0}).then(t=>{let e=null;for(let i=0;i<t.length;i++){const o=t[i];if(o.url===n){e=o;break}}return e?(log_notif_reception("2"),e.focus()):(log_notif_reception("3"),clients.openWindow(n))});t.waitUntil(e)});