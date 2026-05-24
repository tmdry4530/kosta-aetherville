import assert from 'node:assert/strict';
import { test } from 'node:test';

test('foundation client test runner is wired', () => {
  assert.equal(process.env.NODE_ENV ?? 'test', 'test');
});
