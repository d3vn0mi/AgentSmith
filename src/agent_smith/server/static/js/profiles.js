/* Kali profiles page — list + modal form (multiline PEM, proper confirms). */
import { h, icon } from './dom.js';
import { apiRequest } from './api.js';
import { toast } from './toast.js';
import { openModal, closeModal, openConfirm } from './modal.js';
import { renderShell } from './shell.js';

async function loadProfiles() {
    const resp = await apiRequest('/api/profiles');
    if (!resp.ok) { toast.error('Failed to load profiles'); return []; }
    return await resp.json();
}

function renderRow(p, onDelete) {
    return h('tr', null, [
        h('td', null, p.name),
        h('td', { class: 'td-mono' }, `${p.username}@${p.host}:${p.port}`),
        h('td', null, h('span', { class: 'chip chip-dim' }, p.auth_type)),
        h('td', { class: 'td-actions' },
            h('button', {
                class: 'btn btn-sm btn-ghost',
                type: 'button',
                'aria-label': `Delete profile ${p.name}`,
                onclick: onDelete,
            }, icon('trash'))),
    ]);
}

function buildForm() {
    const form = h('form', {
        id: 'profile-form',
        onsubmit: (e) => e.preventDefault(),
    });

    const authSelect = h('select', {
        id: 'pf-auth', name: 'auth_type', class: 'select', required: true,
    }, [
        h('option', { value: 'key' },      'SSH private key'),
        h('option', { value: 'password' }, 'Password'),
    ]);

    const keyField = h('div', { class: 'field' }, [
        h('label', { for: 'pf-key' }, 'SSH private key (PEM)'),
        h('textarea', {
            id: 'pf-key', name: 'key_credential', class: 'textarea',
            placeholder: '-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----',
        }),
        h('p', { class: 'helper' }, 'Stored encrypted at rest using MASTER_KEY.'),
    ]);

    const pwField = h('div', { class: 'field', hidden: true }, [
        h('label', { for: 'pf-pw' }, 'Password'),
        h('input', { id: 'pf-pw', name: 'pw_credential', class: 'input', type: 'password' }),
    ]);

    authSelect.onchange = () => {
        const isKey = authSelect.value === 'key';
        keyField.hidden = !isKey;
        pwField.hidden  = isKey;
    };

    form.append(
        h('div', { class: 'field' }, [
            h('label', { for: 'pf-name' }, 'Profile name'),
            h('input', { id: 'pf-name', name: 'name', class: 'input', required: true }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'pf-host' }, 'Host'),
            h('input', { id: 'pf-host', name: 'host', class: 'input mono', required: true, placeholder: 'kali.internal' }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'pf-port' }, 'SSH port'),
            h('input', {
                id: 'pf-port', name: 'port', class: 'input mono',
                type: 'number', min: '1', max: '65535', value: '22', required: true,
            }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'pf-user' }, 'Username'),
            h('input', { id: 'pf-user', name: 'username', class: 'input mono', required: true }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'pf-auth' }, 'Auth method'),
            authSelect,
        ]),
        keyField,
        pwField,
    );

    function values() {
        const fd = new FormData(form);
        const auth_type = fd.get('auth_type');
        const credential = auth_type === 'key'
            ? form.querySelector('#pf-key').value
            : form.querySelector('#pf-pw').value;
        return {
            name:      fd.get('name'),
            host:      fd.get('host'),
            port:      parseInt(fd.get('port'), 10),
            username:  fd.get('username'),
            auth_type,
            credential,
        };
    }

    return { form, values };
}

function openCreateProfile(onCreated) {
    const { form, values } = buildForm();
    openModal({
        title: 'New Kali profile',
        body: form,
        actions: [
            { label: 'Cancel', kind: 'ghost', onclick: closeModal },
            {
                label: 'Save profile', kind: 'primary',
                onclick: async () => {
                    if (!form.reportValidity()) return;
                    const body = values();
                    if (!body.credential) {
                        toast.error('Credential is required');
                        return;
                    }
                    const resp = await apiRequest('/api/profiles', {
                        method: 'POST',
                        body: JSON.stringify(body),
                    });
                    const data = await resp.json().catch(() => ({}));
                    if (!resp.ok) { toast.error(data.detail || 'Save failed'); return; }
                    toast.success('Profile saved');
                    closeModal();
                    onCreated?.();
                },
            },
        ],
    });
}

export async function renderProfiles() {
    const profiles = await loadProfiles();
    const header = h('div', { class: 'page-header' }, [
        h('h1', null, 'Kali profiles'),
        h('div', { class: 'page-actions' },
            h('button', {
                class: 'btn btn-primary', type: 'button',
                onclick: () => openCreateProfile(renderProfiles),
            }, [icon('plus'), ' New profile'])),
    ]);

    let body;
    if (profiles.length === 0) {
        body = h('div', { class: 'empty-state' },
            'No profiles yet — add your Kali attack box to start a mission.');
    } else {
        const tbody = h('tbody');
        for (const p of profiles) {
            tbody.appendChild(renderRow(p, async () => {
                const ok = await openConfirm({
                    title: 'Delete profile?',
                    message: `Delete "${p.name}"? Missions using it will fail on next run.`,
                    confirmLabel: 'Delete',
                });
                if (!ok) return;
                const resp = await apiRequest(`/api/profiles/${p.id}`, { method: 'DELETE' });
                if (!resp.ok) { toast.error('Delete failed'); return; }
                toast.success('Profile deleted');
                renderProfiles();
            }));
        }
        body = h('div', { class: 'panel' },
            h('table', { class: 'data-table' }, [
                h('thead', null, h('tr', null, [
                    h('th', null, 'Name'),
                    h('th', null, 'Endpoint'),
                    h('th', null, 'Auth'),
                    h('th', null, ''),
                ])),
                tbody,
            ]));
    }

    renderShell(h('div', { class: 'page' }, [header, body]));
}
