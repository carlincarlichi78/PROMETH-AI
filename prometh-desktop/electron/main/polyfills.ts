/**
 * Polyfills para APIs del browser que pdfjs-dist necesita en Node.js/Electron main process.
 * Este archivo DEBE importarse antes que cualquier modulo que use pdf-parse/pdfjs-dist.
 *
 * pdfjs-dist v5 requiere DOMMatrix y Path2D que no existen en Node.js.
 */

if (typeof globalThis.DOMMatrix === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(globalThis as any).DOMMatrix = class DOMMatrix {
    m11 = 1; m12 = 0; m13 = 0; m14 = 0
    m21 = 0; m22 = 1; m23 = 0; m24 = 0
    m31 = 0; m32 = 0; m33 = 1; m34 = 0
    m41 = 0; m42 = 0; m43 = 0; m44 = 1
    a = 1; b = 0; c = 0; d = 1; e = 0; f = 0
    is2D = true; isIdentity = true

    constructor(init?: number[]) {
      if (Array.isArray(init) && init.length === 6) {
        this.a = init[0]; this.b = init[1]; this.c = init[2]
        this.d = init[3]; this.e = init[4]; this.f = init[5]
        this.m11 = init[0]; this.m12 = init[1]; this.m21 = init[2]
        this.m22 = init[3]; this.m41 = init[4]; this.m42 = init[5]
        this.isIdentity = false
      }
    }
    inverse() { return new DOMMatrix() }
    multiply() { return new DOMMatrix() }
    scale() { return new DOMMatrix() }
    translate() { return new DOMMatrix() }
    transformPoint(p?: { x: number; y: number }) { return p || { x: 0, y: 0, z: 0, w: 1 } }
  }
}

if (typeof globalThis.Path2D === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(globalThis as any).Path2D = class Path2D {
    addPath() { /* noop */ }
    closePath() { /* noop */ }
    moveTo() { /* noop */ }
    lineTo() { /* noop */ }
    bezierCurveTo() { /* noop */ }
    quadraticCurveTo() { /* noop */ }
    arc() { /* noop */ }
    arcTo() { /* noop */ }
    ellipse() { /* noop */ }
    rect() { /* noop */ }
  }
}
