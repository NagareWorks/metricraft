const assert = require('node:assert/strict');
const test = require('node:test');
const resolve = require('./ci-command.cjs');

function fixture() {
  const calls = [];
  const context = {
    eventName: 'issue_comment',
    repo: { owner: 'example', repo: 'sdk' },
    sha: 'a'.repeat(40),
    actor: 'rerun-actor',
    payload: {
      action: 'created',
      issue: { number: 17, pull_request: {} },
      comment: { body: '/ci run', user: { login: 'reviewer' }, author_association: 'NONE' },
    },
  };
  const access = { permission: 'write' };
  const pr = { state: 'open', head: { sha: 'b'.repeat(40), repo: { full_name: 'fork/sdk' } } };
  const github = { rest: {
    repos: { getCollaboratorPermissionLevel: async (args) => {
      calls.push(['permission', args]);
      return { data: access };
    } },
    pulls: { get: async (args) => {
      calls.push(['pull', args]);
      return { data: pr };
    } },
  } };
  return { github, context, calls, access, pr };
}

test('both commands resolve a fork PR to its immutable head, after checking the commenter', async () => {
  for (const command of ['/ci run', '/ci run compatibility', '/ci run compatibility\r\n']) {
    const f = fixture();
    f.context.payload.comment.body = command;
    assert.deepEqual(await resolve(f), { repository: 'fork/sdk', sha: 'b'.repeat(40), pr: '17' });
    assert.deepEqual(f.calls, [
      ['permission', { owner: 'example', repo: 'sdk', username: 'reviewer' }],
      ['pull', { owner: 'example', repo: 'sdk', pull_number: 17 }],
    ]);
  }
});

test('same-repository heads and maintain/admin permissions are supported', async () => {
  for (const permission of ['maintain', 'admin']) {
    const f = fixture();
    f.access.permission = permission;
    f.pr.head.repo.full_name = 'example/sdk';
    assert.equal((await resolve(f)).repository, 'example/sdk');
  }
});

test('read/triage/unknown roles cannot authorize work, even with MEMBER association', async () => {
  for (const permission of ['read', 'triage', 'none', undefined]) {
    const f = fixture();
    f.access.permission = permission;
    f.context.payload.comment.author_association = 'MEMBER';
    await assert.rejects(resolve(f), /requires repository write access/);
    assert.equal(f.calls.length, 1);
  }
});

test('unsupported commands, extra arguments and quoted text never call the API', async () => {
  for (const body of [
    '', 'please /ci run', '> /ci run', '```\n/ci run\n```', '/ci runner',
    '/ci run unknown', '/ci run compatibility main', '/ci run; echo unsafe',
    '/ci run\n/ci run compatibility', '/ci run\nthanks',
  ]) {
    const f = fixture();
    f.context.payload.comment.body = body;
    assert.equal(await resolve(f), null);
    assert.deepEqual(f.calls, []);
  }
});

test('ordinary issues, edits and other events cannot start work', async () => {
  for (const modify of [
    (c) => { delete c.payload.issue.pull_request; },
    (c) => { c.payload.action = 'edited'; },
    (c) => { c.eventName = 'pull_request'; },
  ]) {
    const f = fixture();
    modify(f.context);
    assert.equal(await resolve(f), null);
    assert.deepEqual(f.calls, []);
  }
});

test('unavailable authorization fails closed without reading a PR', async () => {
  const f = fixture();
  f.github.rest.repos.getCollaboratorPermissionLevel = async () => { throw new Error('API unavailable'); };
  await assert.rejects(resolve(f), /API unavailable/);
  assert.deepEqual(f.calls, []);
});

test('closed PRs, deleted forks and invalid revisions fail before execution', async () => {
  for (const modify of [
    (pr) => { pr.state = 'closed'; },
    (pr) => { pr.head.repo = null; },
    (pr) => { pr.head.sha = 'main'; },
    (pr) => { pr.head.sha = 'b'.repeat(40) + '\necho unsafe'; },
  ]) {
    const f = fixture();
    modify(f.pr);
    await assert.rejects(resolve(f));
  }
});

test('manual dispatch preserves the selected workflow commit without a PR lookup', async () => {
  const f = fixture();
  f.context.eventName = 'workflow_dispatch';
  f.context.payload = {};
  assert.deepEqual(await resolve(f), { repository: 'example/sdk', sha: 'a'.repeat(40), pr: '' });
  assert.deepEqual(f.calls, []);
});
