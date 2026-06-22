/**
 * @jest-environment jsdom
 */

global.CSRF_TOKEN = 'test-token'

global.fetch = jest.fn(() => Promise.resolve({
    json: () => Promise.resolve([])
}))

document.body.innerHTML = `
    <div id="event-container"></div>
    <div id="gcal-sidebar"></div>
`

const { formatParameterList, minutesToHHMM } = require('./add-event.js')

describe('formatParameterList', () => {

    test('empty array returns empty string', () => {
        expect(formatParameterList('filter', [])).toBe('')
    })

    test('single value formats as ?name=val', () => {
        expect(formatParameterList('filter', ['work'])).toBe('?filter=work')
    })

    test('multiple values join with &', () => {
        expect(formatParameterList('filter', ['work', 'hobbies'])).toBe('?filter=work&filter=hobbies')
    })

})

describe('minutesToHHMM', () => {

    test('zero returns 00:00', () => {
        expect(minutesToHHMM(0)).toBe('00:00')
    })

    test('single digit hour is zero-padded', () => {
        expect(minutesToHHMM(540)).toBe('09:00')
    })

    test('single digit minute is zero-padded', () => {
        expect(minutesToHHMM(485)).toBe('08:05')
    })

    test('full hour only', () => {
        expect(minutesToHHMM(720)).toBe('12:00')
    })

    test('non-whole hour', () => {
        expect(minutesToHHMM(630)).toBe('10:30')
    })

})
