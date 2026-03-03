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

  test('build mode adds -a with default 99 iterations', () => {
    const args = buildArgs({}, 'build');
    expect(args).toEqual(['-a', '-i', '99']);
  });

  test('design mode adds -d, no -a, no -i', () => {
    const args = buildArgs({ interactive: true }, 'design');
    expect(args).toEqual(['-d']);
  });

  test('interactive mode omits -a flag', () => {
    const args = buildArgs({ interactive: true }, 'plan');
    expect(args).toEqual(['-p', '-i', '3']);
  });

  test('custom iterations overrides default', () => {
    const args = buildArgs({ iterations: '10' }, 'build');
    expect(args).toEqual(['-a', '-i', '10']);
  });

  test('idea flag adds -I with text', () => {
    const args = buildArgs({ idea: 'Add auth' }, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3', '-I', 'Add auth']);
  });

  test('new flag adds -n', () => {
    const args = buildArgs({ new: true }, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3', '-n']);
  });

  test('earlyExit false adds -e flag', () => {
    const args = buildArgs({ earlyExit: false }, 'build');
    expect(args).toEqual(['-a', '-i', '99', '-e']);
  });

  test('earlyExit undefined does not add -e', () => {
    const args = buildArgs({}, 'build');
    expect(args).not.toContain('-e');
  });

  test('all flags combined', () => {
    const args = buildArgs({
      interactive: true,
      iterations: '5',
      idea: 'Fix bug',
      new: true,
      earlyExit: false,
    }, 'build');
    expect(args).toEqual(['-i', '5', '-I', 'Fix bug', '-n', '-e']);
  });
});
