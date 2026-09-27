/*
 * SMIP — Comportamiento cliente (Fase 2)
 * - Consulta /health al cargar y al pulsar botón.
 * - Envía archivos a /upload mediante FormData (multipart).
 * - Refresca la lista de archivos desde /files.
 * - Descarga archivos desde /download/{nombre}.
 */
(function () {
  'use strict';

  // ---------- Elementos del DOM ----------
  var badge = document.getElementById('status-badge');
  var statusMsg = document.getElementById('status-message');
  var healthBtn = document.getElementById('health-btn');
  var healthResult = document.getElementById('health-result');
  var uploadForm = document.getElementById('upload-form');
  var fileInput = document.getElementById('file-input');
  var uploadBtn = document.getElementById('upload-btn');
  var uploadResult = document.getElementById('upload-result');
  var filesList = document.getElementById('files-list');
  var filesEmpty = document.getElementById('files-empty');
  var refreshBtn = document.getElementById('refresh-btn');

  // ---------- Utilidades ----------
  function setBadge(state, text) {
    badge.className = 'badge' + (state ? ' ' + state : '');
    badge.textContent = '';
    if (state === 'success') {
      badge.appendChild(document.createTextNode('OK ' + text));
    } else if (state === 'error') {
      badge.appendChild(document.createTextNode('ERROR ' + text));
    } else {
      var spinner = document.createElement('span');
      spinner.className = 'spinner';
      badge.appendChild(spinner);
      badge.appendChild(document.createTextNode(text));
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    var units = ['B', 'KB', 'MB', 'GB'];
    var i = 0;
    var size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i += 1;
    }
    return size.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
  }

  function showHealth(data) {
    var lines = [
      'HTTP 200 — /health',
      '',
      'status: ' + (data.status || 'desconocido'),
      'service: ' + (data.service || 'desconocido'),
      'phase: ' + (data.phase !== undefined ? data.phase : 'desconocido'),
      '',
      'Timestamp: ' + new Date().toISOString(),
    ].join('\n');
    healthResult.textContent = lines;
  }

  function showHealthError(msg) {
    healthResult.textContent = '[Error] ' + escapeHtml(msg);
  }

  function showUploadResult(data) {
    uploadResult.className = 'result-box';
    if (data && data.ok) {
      uploadResult.classList.add('result-success');
      uploadResult.innerHTML =
        '<span class="result-icon">✓</span> ' +
        'Archivo subido: <strong>' + escapeHtml(data.name) + '</strong> ' +
        '(' + formatSize(data.size) + ')';
    } else {
      uploadResult.classList.add('result-error');
      var msg = (data && data.error) ? data.error : 'Operación rechazada.';
      uploadResult.innerHTML =
        '<span class="result-icon">✗</span> ' + escapeHtml(msg);
    }
  }

  // ---------- Health check ----------
  function checkHealth() {
    healthResult.textContent = 'Consultando...';
    setBadge('', 'Conectando...');
    statusMsg.textContent = '';

    fetch('/health', { headers: { Accept: 'application/json' } })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(showHealth)
      .catch(function (err) {
        showHealthError(err.message || String(err));
        setBadge('error', 'No disponible');
        statusMsg.textContent = 'No se pudo contactar con el servicio.';
      })
      .finally(function () {
        healthBtn.disabled = false;
      });
  }

  healthBtn.addEventListener('click', function () {
    healthBtn.disabled = true;
    checkHealth();
  });

  // ---------- Subida de archivo ----------
  uploadForm.addEventListener('submit', function (e) {
    e.preventDefault();

    var file = fileInput.files && fileInput.files[0];
    if (!file) {
      uploadResult.className = 'result-box result-error';
      uploadResult.innerHTML =
        '<span class="result-icon">✗</span> Selecciona un archivo primero.';
      return;
    }

    // Validación local de tamaño (10 MB)
    var MAX_BYTES = 10 * 1024 * 1024;
    if (file.size > MAX_BYTES) {
      uploadResult.className = 'result-box result-error';
      uploadResult.innerHTML =
        '<span class="result-icon">✗</span> El archivo excede el límite de 10 MB.';
      return;
    }

    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Subiendo...';
    uploadResult.className = 'result-box';
    uploadResult.textContent = 'Subiendo ' + escapeHtml(file.name) + '...';

    var formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
      method: 'POST',
      body: formData,
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        showUploadResult(data);
        if (data && data.ok) {
          statusMsg.textContent = 'Archivo "' + data.name + '" almacenado.';
          refreshFiles();
        }
      })
      .catch(function (err) {
        uploadResult.className = 'result-box result-error';
        var msg = err.message || String(err);
        if (err.status === 413 || msg.indexOf('413') !== -1) {
          msg = 'Archivo demasiado grande (límite: 10 MB).';
        }
        uploadResult.innerHTML =
          '<span class="result-icon">✗</span> ' + escapeHtml(msg);
        statusMsg.textContent = 'Error al subir el archivo.';
      })
      .finally(function () {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Subir';
      });
  });

  // ---------- Listado de archivos ----------
  function renderFiles(files) {
    filesList.innerHTML = '';

    if (!files || files.length === 0) {
      filesList.hidden = true;
      filesEmpty.style.display = '';
      return;
    }

    filesList.hidden = false;
    filesEmpty.style.display = 'none';

    files.forEach(function (entry) {
      var li = document.createElement('li');
      li.className = 'file-item';

      var info = document.createElement('div');
      info.className = 'file-info';

      var nameSpan = document.createElement('span');
      nameSpan.className = 'file-name';
      nameSpan.textContent = entry.name;

      var sizeSpan = document.createElement('span');
      sizeSpan.className = 'file-size';
      sizeSpan.textContent = formatSize(entry.size || 0);

      info.appendChild(nameSpan);
      info.appendChild(sizeSpan);

      // Descargar desde Supabase Storage usando la URL pública
      var downloadLink = document.createElement('a');
      downloadLink.href = entry.download_url || '/download/' + encodeURIComponent(entry.name);
      downloadLink.className = 'btn-secondary';
      downloadLink.textContent = 'Descargar';
      downloadLink.target = '_blank';
      downloadLink.rel = 'noopener noreferrer';

      li.appendChild(info);
      li.appendChild(downloadLink);
      filesList.appendChild(li);
    });
  }

  function refreshFiles() {
    fetch('/files', { headers: { Accept: 'application/json' } })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        renderFiles(data.files || []);
        statusMsg.textContent = 'Lista actualizada: ' +
          (data.files ? data.files.length : 0) + ' archivo(s).';
      })
      .catch(function (err) {
        statusMsg.textContent = 'No se pudo obtener la lista.';
        console.error('Error refreshFiles:', err);
      });
  }

  refreshBtn.addEventListener('click', refreshFiles);

  // ---------- Envío de correo (Fase 3) ----------
  var emailForm = document.getElementById('email-form');
  var emailTo = document.getElementById('email-to');
  var emailSubject = document.getElementById('email-subject');
  var emailMessage = document.getElementById('email-message');
  var emailSendBtn = document.getElementById('email-send-btn');
  var emailResult = document.getElementById('email-result');

  // ---------- Historial de mensajes ----------
  var messagesList = document.getElementById('messages-list');
  var messagesEmpty = document.getElementById('messages-empty');
  var refreshMessagesBtn = document.getElementById('refresh-messages');
  var clearMessagesBtn = document.getElementById('clear-messages');
  var messagesContainer = document.getElementById('messages-container');

  function renderMessages(messages) {
    messagesList.innerHTML = '';

    if (!messages || messages.length === 0) {
      messagesList.style.display = 'none';
      messagesEmpty.style.display = '';
      return;
    }

    messagesList.style.display = 'flex';
    messagesEmpty.style.display = 'none';

    // Mostrar los últimos 20 mensajes, ordenados del más reciente al más viejo
    var recentMessages = messages.slice(-20).reverse();

    recentMessages.forEach(function (msg) {
      var item = document.createElement('div');
      item.className = 'message-item' + (msg.success ? ' success' : ' error');

      var header = document.createElement('div');
      header.className = 'message-header';

      var toSpan = document.createElement('span');
      toSpan.className = 'message-to';
      toSpan.textContent = 'Para: ' + escapeHtml(msg.to);

      var statusSpan = document.createElement('span');
      statusSpan.className = 'message-status ' + (msg.success ? 'sent' : 'failed');
      statusSpan.textContent = msg.success ? '✓ Enviado' : '✗ Fallido';

      header.appendChild(toSpan);
      header.appendChild(statusSpan);

      var subjectDiv = document.createElement('div');
      subjectDiv.className = 'message-subject';
      subjectDiv.textContent = escapeHtml(msg.subject);

      var bodyDiv = document.createElement('div');
      bodyDiv.className = 'message-body';
      bodyDiv.textContent = escapeHtml(msg.message);

      var metaDiv = document.createElement('div');
      metaDiv.className = 'message-meta';

      var dateSpan = document.createElement('span');
      var date = new Date(msg.timestamp);
      dateSpan.textContent = date.toLocaleString();

      metaDiv.appendChild(dateSpan);

      item.appendChild(header);
      item.appendChild(subjectDiv);
      item.appendChild(bodyDiv);
      item.appendChild(metaDiv);

      messagesList.appendChild(item);
    });
  }

  function refreshMessages() {
    fetch('/messages', { headers: { Accept: 'application/json' } })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        renderMessages(data.messages || []);
        statusMsg.textContent = 'Historial actualizado: ' +
          (data.messages ? data.messages.length : 0) + ' mensaje(s).';
      })
      .catch(function (err) {
        statusMsg.textContent = 'No se pudo obtener el historial.';
        console.error('Error refreshMessages:', err);
      });
  }

  refreshMessagesBtn.addEventListener('click', refreshMessages);

  clearMessagesBtn.addEventListener('click', function () {
    if (confirm('¿Estás seguro de que quieres limpiar todo el historial de mensajes?')) {
      fetch('/messages/clear', { method: 'GET' })
        .then(function (resp) {
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          return resp.json();
        })
        .then(function (data) {
          messagesList.innerHTML = '';
          messagesList.style.display = 'none';
          messagesEmpty.style.display = '';
          statusMsg.textContent = 'Historial limpiado (' + data.cleared + ' mensaje(s) eliminados).';
        })
        .catch(function (err) {
          statusMsg.textContent = 'No se pudo limpiar el historial.';
          console.error('Error clearMessages:', err);
        });
    }
  });

  // ---------- Envío de correo (Fase 3) ----------

  function showEmailResult(data) {
    emailResult.className = 'result-box';
    if (data && data.ok) {
      emailResult.classList.add('result-success');
      emailResult.innerHTML =
        '<span class="result-icon">✓</span> ' +
        escapeHtml(data.message || 'Correo enviado correctamente.');
    } else {
      emailResult.classList.add('result-error');
      var msg = (data && data.message) ? data.message : 'No se pudo enviar el correo.';
      emailResult.innerHTML =
        '<span class="result-icon">✗</span> ' + escapeHtml(msg);
      statusMsg.textContent = 'Error al enviar el correo.';
    }
  }

  emailForm.addEventListener('submit', function (e) {
    e.preventDefault();

    var to = emailTo.value.trim();
    var subject = emailSubject.value.trim();
    var message = emailMessage.value.trim();

    if (!to || !subject || !message) {
      emailResult.className = 'result-box result-error';
      emailResult.innerHTML =
        '<span class="result-icon">✗</span> Completa todos los campos.';
      return;
    }

    emailSendBtn.disabled = true;
    emailSendBtn.textContent = 'Enviando...';
    emailResult.className = 'result-box';
    emailResult.textContent = 'Enviando correo...';

    fetch('/send-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to: to, subject: subject, message: message }),
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        showEmailResult(data);
        if (data && data.ok) {
          statusMsg.textContent = 'Correo enviado a ' + to + '.';
        }
      })
      .catch(function (err) {
        emailResult.className = 'result-box result-error';
        var msg = err.message || String(err);
        if (err.status === 500 && msg.indexOf('no configurado') !== -1) {
          msg = 'SMTP no configurado. Define las variables SMTP_* (ver .env.example).';
        }
        emailResult.innerHTML =
          '<span class="result-icon">✗</span> ' + escapeHtml(msg);
        statusMsg.textContent = 'Error al enviar el correo.';
      })
      .finally(function () {
        emailSendBtn.disabled = false;
        emailSendBtn.textContent = 'Enviar correo';
      });
  });

  // ---------- Descarga ----------
  function downloadFile(name) {
    var encoded = encodeURIComponent(name);
    var url = '/download/' + encoded;
    var req = new XMLHttpRequest();
    req.open('GET', url, true);
    req.responseType = 'blob';
    req.onload = function () {
      if (req.status === 200) {
        var blob = req.response;
        var blobUrl = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = blobUrl;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(blobUrl); }, 1000);
        statusMsg.textContent = 'Descargando: ' + name;
      } else {
        statusMsg.textContent = 'Error al descargar: HTTP ' + req.status;
      }
    };
    req.onerror = function () {
      statusMsg.textContent = 'Error de red al descargar.';
    };
    req.send();
  }

  // ---------- Inicialización ----------
  window.addEventListener('DOMContentLoaded', function () {
    setTimeout(checkHealth, 600);
    setTimeout(refreshFiles, 1000);
  });
})();
