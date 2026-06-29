// Shared share-bar builder, used by the main app (script.js) and the /story
// page. buildShareBar(opts) returns a .share-bar element; the caller appends it.
(function () {
    function makeShareButton(label, onClick) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'share-button';
        b.textContent = label;
        b.addEventListener('click', onClick);
        return b;
    }

    window.buildShareBar = function (opts) {
        const url = opts.url;
        const title = opts.title || '';

        const bar = document.createElement('div');
        bar.className = 'share-bar';

        // Native share sheet — on mobile / supported browsers this covers every
        // app the user has (Messages, WhatsApp, Mail, social, etc.) in one tap.
        if (navigator.share) {
            bar.appendChild(makeShareButton('📤 Share', function () {
                navigator.share({ title: 'ChatLibs', text: title, url: url })
                    .catch(function () { /* user cancelled */ });
            }));
        }

        // Copy link — the universal fallback that works everywhere, including
        // browsers without the Web Share API (e.g. Firefox desktop).
        const copyBtn = makeShareButton('🔗 Copy Link', function () {
            navigator.clipboard.writeText(url).then(function () {
                copyBtn.textContent = '✓ Copied!';
                setTimeout(function () { copyBtn.textContent = '🔗 Copy Link'; }, 1500);
            }).catch(function () { copyBtn.textContent = 'Copy failed'; });
        });
        bar.appendChild(copyBtn);

        return bar;
    };
})();
