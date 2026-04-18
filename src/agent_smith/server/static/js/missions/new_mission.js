/* New Mission modal — form replacing the old 4-prompt chain. */
import { h } from '../dom.js';
import { apiRequest } from '../api.js';
import { openModal, closeModal } from '../modal.js';
import { toast } from '../toast.js';
import { navigate } from '../router.js';

export async function openNewMissionModal() {
    const [profilesResp, playbooksResp] = await Promise.all([
        apiRequest('/api/profiles'),
        apiRequest('/api/playbooks'),
    ]);
    if (!profilesResp.ok || !playbooksResp.ok) {
        toast.error('Failed to load profiles or playbooks');
        return;
    }
    const profiles  = await profilesResp.json();
    const playbooks = await playbooksResp.json();

    if (profiles.length === 0) {
        toast.warn('Create a Kali profile first');
        navigate('profiles');
        return;
    }
    if (playbooks.length === 0) {
        toast.error('No playbooks on disk');
        return;
    }

    const form = h('form', {
        id: 'new-mission-form',
        onsubmit: (e) => { e.preventDefault(); submit(); },
    }, [
        h('div', { class: 'field' }, [
            h('label', { for: 'nm-name' }, 'Mission name'),
            h('input', { id: 'nm-name', name: 'name', class: 'input', required: true, autocomplete: 'off' }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'nm-target' }, 'Target (IP or hostname)'),
            h('input', { id: 'nm-target', name: 'target', class: 'input mono', required: true, autocomplete: 'off', placeholder: '10.10.11.5' }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'nm-profile' }, 'Kali profile'),
            h('select', { id: 'nm-profile', name: 'profile', class: 'select', required: true },
                profiles.map(p => h('option', { value: p.id }, `${p.name} — ${p.username}@${p.host}:${p.port}`))),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'nm-playbook' }, 'Playbook'),
            h('select', { id: 'nm-playbook', name: 'playbook', class: 'select', required: true },
                playbooks.map(p => h('option', { value: p.filename },
                    p.description ? `${p.name} — ${p.description}` : p.name))),
        ]),
    ]);

    async function submit() {
        const fd = new FormData(form);
        const body = {
            name:            fd.get('name'),
            target:          fd.get('target'),
            playbook:        fd.get('playbook'),
            kali_profile_id: fd.get('profile'),
        };
        const resp = await apiRequest('/api/missions', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            toast.error(data.detail || 'Mission creation failed');
            return;
        }
        toast.success(`Mission "${body.name}" started`);
        closeModal();
        navigate(`mission/${data.id}`);
    }

    openModal({
        title: 'New mission',
        body: form,
        actions: [
            { label: 'Cancel',        kind: 'ghost',   onclick: closeModal },
            { label: 'Start mission', kind: 'primary', onclick: () => form.requestSubmit() },
        ],
    });
}
