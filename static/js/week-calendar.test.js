/**
 * @jest-environment jsdom
 */

// Set up DOM before requiring the file
document.body.innerHTML = `
    <div id="grid-container"></div>
    <div id="week-js" data-week="2026-04-06"></div>
    <div id="dateText"></div>
`

const { getDayIndex, buildGrid } = require('./week-calendar.js')

describe('getDayIndex', () => {

    test('Sunday (0) should return 6', () => {
        expect(getDayIndex(0)).toBe(6)
    })

    test('Monday (1) should return 0', () => {
        expect(getDayIndex(1)).toBe(0)
    })

    test('Tuesday (2) should return 1', () => {
        expect(getDayIndex(2)).toBe(1)
    })

    test('Wednesday (3) should return 2', () => {
        expect(getDayIndex(3)).toBe(2)
    })

    test('Thursday (4) should return 3', () => {
        expect(getDayIndex(4)).toBe(3)
    })

    test('Friday (5) should return 4', () => {
        expect(getDayIndex(5)).toBe(4)
    })

    test('Saturday (6) should return 5', () => {
        expect(getDayIndex(6)).toBe(5)
    })

})

describe('buildGrid creates correct structure', () => {

    test('grid container should have children after buildGrid', () => {
        const grid = document.getElementById('grid-container')
        expect(grid.children.length).toBeGreaterThan(0)
    })

    test('should create 7 day label columns', () => {
        const dayLabels = document.querySelectorAll('.dayOfTheWeek')
        expect(dayLabels.length).toBe(7)
    })

    test('should create 24 time labels', () => {
        const timeLabels = document.querySelectorAll('.time-label')
        expect(timeLabels.length).toBe(24)
    })

    test('each hour slot should have 4 items (15-min slots)', () => {
        const hourSlots = document.querySelectorAll('.hour-slot')
        hourSlots.forEach(slot => {
            expect(slot.querySelectorAll('.item').length).toBe(4)
        })
    })

    test('items should have correct data-day attribute range (0-6)', () => {
        const items = document.querySelectorAll('.item')
        items.forEach(item => {
            const day = parseInt(item.dataset.day)
            expect(day).toBeGreaterThanOrEqual(0)
            expect(day).toBeLessThanOrEqual(6)
        })
    })

    test('items should have correct data-minute values (0, 15, 30, 45)', () => {
        const validMinutes = ['0', '15', '30', '45']
        const items = document.querySelectorAll('.item')
        items.forEach(item => {
            expect(validMinutes).toContain(item.dataset.minute)
        })
    })

})

describe('display sets dateText correctly', () => {

    test('dateText element exists in the DOM', () => {
        const dateText = document.getElementById('dateText')
        expect(dateText).not.toBeNull()
    })

    test('display runs without throwing an error', () => {
        const { display } = require('./week-calendar.js')
        expect(() => display(new Date('2026-04-06'))).not.toThrow()
    })

})