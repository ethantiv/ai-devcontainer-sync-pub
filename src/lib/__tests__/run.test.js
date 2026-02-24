const { runDesign } = require('../run');

describe('runDesign', () => {
  test('is exported as a function', () => {
    expect(typeof runDesign).toBe('function');
  });
});
