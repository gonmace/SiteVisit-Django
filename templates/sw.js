{% load static %}/* SiteVisit service worker — v1
   Solo gestiona Web Push; sin cache offline.
   Cambiar el número de versión fuerza la actualización del SW en los clientes. */

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { /* payload no JSON */ }
  const title = data.title || 'SiteVisit';
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || '',
    icon: '{% static "img/icon-192.png" %}',
    badge: '{% static "img/icon-192.png" %}',
    data: { url: data.url || '/manager/' },
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/manager/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (client.url.includes('/manager/') && 'focus' in client) {
          client.focus();
          return client.navigate(url);
        }
      }
      return clients.openWindow(url);
    })
  );
});
