document.addEventListener('DOMContentLoaded', () => {
    const openModal = id => {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.remove('hidden');
        if (id === 'stockModal') {
            initTickerAutocomplete();
            initTagAutocomplete();
        }
    };

    const closeModal = modal => modal.classList.add('hidden');

    document.querySelectorAll('.open-modal-btn').forEach(btn =>
        btn.addEventListener('click', () => openModal(btn.dataset.target))
    );
    document.querySelectorAll('.modal-close').forEach(btn =>
        btn.addEventListener('click', () => closeModal(btn.closest('.modal')))
    );
    window.addEventListener('click', e => {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target);
        }
    });

    function initTickerAutocomplete() {
        const input = document.getElementById('stock-input');
        const list  = document.getElementById('ticker-suggestions');
        input.addEventListener('input', () => {
            const q = input.value.trim();
            if (!q) {
                list.innerHTML = '';
                return list.classList.add('hidden');
            }
            fetch(`/api/autocomplete/tickers/?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    list.innerHTML = '';
                    if (!data.length) return list.classList.add('hidden');
                    data.forEach(item => {
                        const li = document.createElement('li');
                        li.textContent = item.label;
                        li.dataset.ticker = item.ticker;
                        li.className = 'px-2 py-1 hover:bg-indigo-700 cursor-pointer text-gray-100';
                        li.addEventListener('click', () => {
                            input.value = li.dataset.ticker;
                            list.innerHTML = '';
                            list.classList.add('hidden');
                        });
                        list.appendChild(li);
                    });
                    list.classList.remove('hidden');
                });
        });
    }

    function initTagAutocomplete() {
        const input = document.getElementById('tags-input');
        const list  = document.getElementById('tags-suggestions');
        input.addEventListener('input', () => {
            const q = input.value.trim();
            if (!q) {
                list.innerHTML = '';
                return list.classList.add('hidden');
            }
            fetch(`/api/autocomplete/tags/?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    list.innerHTML = '';
                    if (!data.length) return list.classList.add('hidden');
                    data.forEach(item => {
                        const li = document.createElement('li');
                        li.textContent = item.label;
                        li.className = 'px-2 py-1 hover:bg-indigo-700 cursor-pointer text-gray-100';
                        li.addEventListener('click', () => {
                            const parts = input.value.split(',').map(s => s.trim()).filter(Boolean);
                            if (!parts.includes(item.label)) parts.push(item.label);
                            input.value = parts.join(', ');
                            list.innerHTML = '';
                            list.classList.add('hidden');
                        });
                        list.appendChild(li);
                    });
                    list.classList.remove('hidden');
                });
        });
    }
});
