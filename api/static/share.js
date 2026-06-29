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

    function makeShareLink(label, href, newTab) {
        const a = document.createElement('a');
        a.className = 'share-button';
        a.textContent = label;
        a.href = href;
        if (newTab) { a.target = '_blank'; a.rel = 'noopener'; }
        return a;
    }

    window.buildShareBar = function (opts) {
        const url = opts.url;
        const title = opts.title || '';
        const imageUrl = opts.imageUrl || '';

        const bar = document.createElement('div');
        bar.className = 'share-bar';

        // Native share sheet (mobile / supported browsers only).
        if (navigator.share) {
            bar.appendChild(makeShareButton('📤 Share', function () {
                navigator.share({ title: 'ChatLibs', text: title, url: url })
                    .catch(function () { /* user cancelled */ });
            }));
        }

        // Copy link.
        const copyBtn = makeShareButton('🔗 Copy Link', function () {
            navigator.clipboard.writeText(url).then(function () {
                copyBtn.textContent = '✓ Copied!';
                setTimeout(function () { copyBtn.textContent = '🔗 Copy Link'; }, 1500);
            }).catch(function () { copyBtn.textContent = 'Copy failed'; });
        });
        bar.appendChild(copyBtn);

        // Email (no new tab — let the mail client open).
        bar.appendChild(makeShareLink('✉️ Email',
            'mailto:?subject=' + encodeURIComponent('A ChatLibs story: ' + title) +
            '&body=' + encodeURIComponent('Check out my silly ChatLibs story: ' + title + '\n\n' + url),
            false));

        // Facebook (URL only — uses the page's Open Graph tags for the preview).
        bar.appendChild(makeShareLink('Facebook',
            'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url), true));

        // Pinterest (image-first; include the hosted image when we have one).
        let pin = 'https://www.pinterest.com/pin/create/button/?url=' +
            encodeURIComponent(url) + '&description=' + encodeURIComponent(title);
        if (imageUrl) pin += '&media=' + encodeURIComponent(imageUrl);
        bar.appendChild(makeShareLink('Pinterest', pin, true));

        return bar;
    };
})();
