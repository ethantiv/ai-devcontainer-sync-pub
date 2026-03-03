const { runDesign, buildArgs } = require('../run');

describe('runDesign', () => {
  test('is exported as a function', () => {
    expect(typeof runDesign).toBe('function');
  });
});

describe('buildArgs', () => {
  test('plan mode adds -p and -a with default 3 iterations', () => {
    const args = buildArgs({}, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3']);
  });
});
