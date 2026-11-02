// static/js/objectDetection.js — Doun Industries: Object Detection tool window.
//
// Placeholder only. This opens and closes the #objdetect-modal window from the
// sidebar (#tool-objdetect-btn) and icon rail (#rail-objdetect, routed through
// app.js _railToolMap). No detection model is wired up yet; the input area,
// model picker and Detect button in the window are disabled on purpose.
//
// When detection is added, keep the UI here and put the model call behind a
// backend route (e.g. POST /api/object-detection) so it can run either locally
// or through a hosted API, same as the rest of the app.

import { makeWindowDraggable } from './windowDrag.js';
import { nextToolWindowZ } from './toolWindowZOrder.js';

const MODAL_ID = 'objdetect-modal';

function getModal() {
  return document.getElementById(MODAL_ID);
}

export function openObjectDetection() {
  const modal = getModal();
  if (!modal) return;
  modal.classList.remove('hidden', 'modal-minimized');
  try { modal.style.zIndex = String(nextToolWindowZ({ exclude: modal, current: modal.style.zIndex })); } catch (_) {}
}

export function closeObjectDetection() {
  const modal = getModal();
  if (modal) modal.classList.add('hidden');
}

function toggleObjectDetection() {
  const modal = getModal();
  if (!modal) return;
  if (modal.classList.contains('hidden')) openObjectDetection();
  else closeObjectDetection();
}

function init() {
  const modal = getModal();
  if (!modal || modal.dataset.wired === '1') return;
  modal.dataset.wired = '1';

  document.getElementById('tool-objdetect-btn')?.addEventListener('click', toggleObjectDetection);
  document.getElementById('close-objdetect')?.addEventListener('click', closeObjectDetection);

  // Click on the dimmed backdrop (not the window itself) closes it.
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeObjectDetection();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeObjectDetection();
  });

  const content = modal.querySelector('.modal-content');
  const header = modal.querySelector('.modal-header');
  if (content && header) {
    try {
      makeWindowDraggable(modal, { content, header, skipSelector: '.close-btn', enableDock: false, enableResize: false });
    } catch (e) {
      console.warn('Object Detection: drag setup failed', e);
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}

export default { open: openObjectDetection, close: closeObjectDetection };
