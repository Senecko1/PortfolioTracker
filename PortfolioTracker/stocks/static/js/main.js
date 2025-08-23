document.addEventListener('DOMContentLoaded', () => {
    const openModal = id => {
        const modal = document.getElementById(id);
        if (!modal) return;
            modal.style.display = 'block';
        if (id === 'stockModal') {
            initializeStockAutocomplete();
            initializeTagSelect();
    }
    };

    const closeModal = modal => {
    modal.style.display = 'none';
    if (modal.id === 'stockModal') {
        destroySelect2('#stock-symbol-input');
        destroySelect2('#stock-tags-input');
    }
    };

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

    function initializeTagSelect() {
        const $tagInput = $('#stock-tags-input');
        if ($tagInput.length) {
            if ($tagInput.hasClass('select2-hidden-accessible')) {
                $tagInput.select2('destroy');
            }
            $tagInput.select2({
                tags: true,
                tokenSeparators: [','],
                placeholder: 'Select your tags, e.g. Finance, Technology, etc.',
                width: '100%',
                ajax: {
                    url: '/tag_autocomplete/',
                    dataType: 'json',
                    delay: 100,
                    data: params => ({ q: params.term || '' }),
                    processResults: data => ({ results: data.results || [] }),
                    cache: true
                },
                createTag: params => ({
                    id: params.term.trim(),
                    text: params.term.trim(),
                    newOption: true
                }),
                templateResult: data => data.loading
                    ? 'Searching...'
                    : (data.newOption
                        ? $('<em>New tag: ' + data.text + '</em>')
                        : data.text),
                templateSelection: data => data.text,
                language: {
                    noResults: () => 'No results found',
                    searching: () => 'Searching...',
                    inputTooShort: () => 'Please enter at least 1 character'
                }
            });
        }
    }


    function initializeStockAutocomplete() {
        const $stockInput = $('#stock-symbol-input');
        if ($stockInput.hasClass('select2-hidden-accessible')) {
            $stockInput.select2('destroy');
        }
        $stockInput.select2({
            tags: true,
            tokenSeparators: [','],
            createTag: params => ({
                id: params.term.toUpperCase(),
                text: params.term.toUpperCase() + ' (new)',
                newOption: true
            }),
            ajax: {
                url: '/stock_autocomplete/',
                dataType: 'json',
                delay: 100,
                data: params => ({ q: params.term || '' }),
                processResults: data => ({ results: data.results || [] }),
                cache: true
            },
            placeholder: 'Stock ticker symbol, e.g. AAPL',
            minimumInputLength: 1,
            width: '100%',
            dropdownParent: $('#stockModal'),
            allowClear: true,
            closeOnSelect: true,
            templateResult: data => {
                if (data.loading) return 'Searching...';
                if (data.newOption) return $('<em>New ticker: ‘' + data.id + '’</em>');
                if (data.text.includes('–')) {
                    const parts = data.text.split(' – ');
                    return $('<div><strong>' + parts[0] + '</strong><br><small>' + parts.slice(1).join(' – ') + '</small></div>');
                }
                return data.text || data.id;
            },
            templateSelection: data => data.id || data.text,
            language: {
                noResults: () => 'No results found',
                searching: () => 'Searching...',
                inputTooShort: () => 'Please enter at least 1 character'
            }
        }).on('select2:select', e => {
            $('#stock-symbol-input').val(e.params.data.id);
        }).select2('open');
    }

    function destroySelect2(selector) {
        const $el = $(selector);
        if ($el.length && $el.hasClass('select2-hidden-accessible')) {
            $el.select2('destroy');
        }
    }
});
