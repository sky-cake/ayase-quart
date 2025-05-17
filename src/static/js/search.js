const searchform = document.getElementById('searchform');
const file_upload = document.getElementById('file_upload');

searchform.addEventListener('submit', function (event) {
  const checkboxes = document.querySelectorAll('input[name="boards"]:checked');
  if (checkboxes.length === 0) {
    alert('Please select at least one board.');
    return;
  }

  if (searchform && file_upload) {
    if (file_upload.files.length > 0) {
      searchform.method = 'post';
      searchform.enctype = 'multipart/form-data';
    } else {
      searchform.method = 'get';
      searchform.enctype = '';
    }
  }
  else
  {
    event.preventDefault();
    const form = event.target;
    const params = new URLSearchParams();
    (new FormData(form)).forEach((value, key) => {
      if (value !== "") {
        params.append(key, value);
      }
    });
    const h = window.location.pathname + '?' + params.toString();
    window.location.href = h;
  }
});

if (file_upload) {
  file_upload.addEventListener('change', function (event) {
    const files = event.target.files;
    if (files.length > 1) {
      alert('Please select only one file.');
      event.target.value = '';
      return;
    }
    const file = files[0];
    if (file) {
      const allowedTypes = ['image/png', 'image/jpeg', 'image/gif'];
      if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please select a PNG, JPEG, or GIF image.');
        event.target.value = '';
        return;
      }
      if (file.size > 4.05 * 1024 * 1024) {
        alert('File size exceeds 4MB. Please select a smaller file.');
        event.target.value = '';
        return;
      }
    }
  });
}
