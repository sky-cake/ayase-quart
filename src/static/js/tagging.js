const general_tag_input = document.getElementById('general_tag_input');
const character_tag_input = document.getElementById('character_tag_input');
const file_input = document.getElementById('img');
const general_tag_suggestions = document.getElementById('general_tag_suggestions');
const character_tag_suggestions = document.getElementById('character_tag_suggestions');
const selected_general_tags_div = document.getElementById('selected_general_tags');
const selected_character_tags_div = document.getElementById('selected_character_tags');
const search_button = document.getElementById('search_button');
const clear_button = document.getElementById('clear_button');

let selected_general_tags = [];
let selected_character_tags = [];
let all_tags = new Map();
let results = [];

async function fetch_all_tags() {
  const response = await fetch('/tags');
  const tags = await response.json();
  all_tags = new Map(tags.map(tag => [tag[0], { 0: tag[0], 1: tag[1], 2: tag[2] }]));
  init();
}

function init() {
  const chars = document.getElementById('file_tags_character').value;
  const gens = document.getElementById('file_tags_general').value;
  const char_ids = chars ? chars.split(',').map(Number) : [];
  const gen_ids = gens ? gens.split(',').map(Number) : [];

  selected_character_tags = char_ids
    .map(id => {
      const v = all_tags.get(id);
      return v ? { tag_id: v[0], tag_name: v[1] } : null;
    })
    .filter(tag => tag !== null);

  selected_general_tags = gen_ids
    .map(id => {
      const v = all_tags.get(id);
      return v ? { tag_id: v[0], tag_name: v[1] } : null;
    })
    .filter(tag => tag !== null);

  render_character_tags();
  render_general_tags();
}

fetch_all_tags();

function clear_character_tag_input() {
  document.getElementById('character_tag_input').value = '';
}

function clear_general_tag_input() {
  document.getElementById('general_tag_input').value = '';
}

function handle_tag_input(inputElement, suggestion_container, tag_type_id) {
  const query = inputElement.value.trim().toLowerCase();
  if (query.length === 0) {
    suggestion_container.innerHTML = '';
    return;
  }
  const filtered_tags = Array.from(all_tags.values()).filter(tag => tag[2] === tag_type_id && tag[1].includes(query));
  suggestion_container.innerHTML = filtered_tags.map(tag => `<div class="tag_suggestion" data-id="${tag[0]}">${tag[1]}</div>`).join('');

  if (tag_type_id === 4) {
    attach_suggestion_events(suggestion_container, selected_character_tags, render_character_tags, 'file_tags_character');
  } else {
    attach_suggestion_events(suggestion_container, selected_general_tags, render_general_tags, 'file_tags_general');
  }
}

general_tag_input.addEventListener('input', () => { handle_tag_input(general_tag_input, general_tag_suggestions, 0); });
general_tag_input.addEventListener('focus', () => { handle_tag_input(general_tag_input, general_tag_suggestions, 0); });
character_tag_input.addEventListener('input', () => { handle_tag_input(character_tag_input, character_tag_suggestions, 4); });
character_tag_input.addEventListener('focus', () => { handle_tag_input(character_tag_input, character_tag_suggestions, 4); });

function attach_suggestion_events(suggestions_div, selected_tags, render_fn, hidden_tag_field_id) {
  suggestions_div.querySelectorAll('.tag_suggestion').forEach(suggestion => {
    suggestion.addEventListener('click', () => {
      const tag_id = parseInt(suggestion.getAttribute('data-id'));
      const tag_name = suggestion.textContent.trim();
      if (!selected_tags.some(tag => tag.tag_id === tag_id)) {
        selected_tags.push({ tag_id, tag_name });
        render_fn();
      }
      suggestion.outerHTML = '';
      document.getElementById(hidden_tag_field_id).value = selected_tags.map(tag => tag.tag_id).join(',');
    });
  });
}

function render_general_tags() {
  render_tags(selected_general_tags_div, 'general');
}

function render_character_tags() {
  render_tags(selected_character_tags_div, 'character');
}

function render_tags(container, class_name) {
  const selected_tags = class_name === 'general' ? selected_general_tags : selected_character_tags;
  container.innerHTML = selected_tags.map(tag => `<span class="pill ${class_name}">${tag.tag_name} <button data-id="${tag.tag_id}" type="button">x</button></span>`).join('');

  container.querySelectorAll('button[data-id]').forEach(button => {
    button.addEventListener('click', () => {
      const tag_id = parseInt(button.getAttribute('data-id'));
      if (class_name === 'general') {
        selected_general_tags.splice(selected_general_tags.findIndex(tag => tag.tag_id === tag_id), 1);
        document.getElementById('file_tags_general').value = selected_general_tags.map(tag => tag.tag_id).join(',');
        render_general_tags();
      } else {
        selected_character_tags.splice(selected_character_tags.findIndex(tag => tag.tag_id === tag_id), 1);
        document.getElementById('file_tags_character').value = selected_character_tags.map(tag => tag.tag_id).join(',');
        render_character_tags();
      }
    });
  });
}

function render_tags_text(tags, color) {
  return Object.entries(tags).map(([tag, prob]) => `<span class="pill ${color}">${tag}: ${prob.toFixed(2)}</span>`).join(' ');
}

clear_button.addEventListener('click', () => {
  selected_general_tags = [];
  selected_character_tags = [];

  selected_general_tags_div.innerHTML = '';
  selected_character_tags_div.innerHTML = '';

  general_tag_input.value = '';
  character_tag_input.value = '';
  general_tag_suggestions.innerHTML = '';
  character_tag_suggestions.innerHTML = '';

  document.getElementById('file_tags_character').value = '';
  document.getElementById('file_tags_general').value = '';
});
