// Classic content script: load the ES-module entry point from the extension package.
(async () => { await import(chrome.runtime.getURL("content/main.js")); })();
