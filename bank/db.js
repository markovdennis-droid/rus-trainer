/* ============================================================
   Общее хранилище кабинетов — МАКЕТ.

   Заменяет сервер: держит преподавателей, учеников, приглашения,
   оплаты и сданные работы. Пишет в localStorage, чтобы страницы
   видели общие данные; если браузер его не отдаёт (приватное окно,
   запрет на доступ к данным сайта), молча работает в памяти —
   тогда данные живут до перезагрузки.

   В продукте этот файл заменяется запросами к серверу: те же
   сущности лежат в PostgreSQL, а проверка части 1 и ключи
   остаются на сервере и клиенту не отдаются.
   ============================================================ */
(function (global) {
  "use strict";

  var KEY = "egetraining_demo_v1";
  var memory = null;         // запасное хранилище, если localStorage недоступен
  var storageOk = true;

  var SUBJECTS = [
    { id: "rus", title: "Русский язык",   price: 990, discount: 840, variants: ["v1"] },
    { id: "soc", title: "Обществознание", price: 990, discount: 840, variants: [] }
  ];

  function seed() {
    return {
      subjects: SUBJECTS,
      teachers: [{
        id: "t1",
        name: "Евгения Александровна",
        email: "teacher@example.com",
        percent: 30,
        subjects: ["rus", "soc"]
      }],
      students: [
        { id: "s1", name: "Аня Ковалёва",  teacherId: "t1", subject: "rus",
          status: "paid",    code: "RUS-4821", group: "11 класс · вт/чт", joinedAt: "9 октября" },
        { id: "s2", name: "Миша Лебедев",  teacherId: "t1", subject: "rus",
          status: "paid",    code: "RUS-7390", group: "11 класс · вт/чт", joinedAt: "7 октября" },
        { id: "s3", name: "Соня Гринь",    teacherId: "t1", subject: "rus",
          status: "invited", code: null,       group: "10 класс",         joinedAt: "вчера" }
      ],
      submissions: [],
      /* сессии держим отдельно по ролям: в макете преподаватель и ученик
         открыты в одном браузере, и общая сессия выбивала бы одного из них */
      session: { teacher: null, student: null },
      payments: []
    };
  }

  function read() {
    if (memory && !storageOk) return memory;
    if (storageOk) {
      try {
        var raw = global.localStorage.getItem(KEY);
        if (raw) {
          memory = JSON.parse(raw);
          if (!memory.session || typeof memory.session.teacher === "undefined")
            memory.session = { teacher: null, student: null };
          return memory;
        }
      } catch (e) { storageOk = false; }
    }
    memory = seed();
    write(memory);
    return memory;
  }

  function write(data) {
    memory = data;
    if (!storageOk) return;
    try { global.localStorage.setItem(KEY, JSON.stringify(data)); }
    catch (e) { storageOk = false; }
  }

  function uid(prefix) {
    return prefix + Math.random().toString(36).slice(2, 8);
  }

  function code(subjectId) {
    var n = Math.floor(1000 + Math.random() * 9000);
    return subjectId.toUpperCase() + "-" + n;
  }

  var DB = {
    /* --- доступ к данным --- */
    all: read,
    reset: function () { memory = null; try { global.localStorage.removeItem(KEY); } catch (e) {} return read(); },
    persistent: function () { return storageOk; },

    subject: function (id) { return read().subjects.filter(function (s) { return s.id === id; })[0]; },
    teacher: function (id) { return read().teachers.filter(function (t) { return t.id === id; })[0]; },
    student: function (id) { return read().students.filter(function (s) { return s.id === id; })[0]; },

    studentsOf: function (teacherId, subjectId) {
      return read().students.filter(function (s) {
        return s.teacherId === teacherId && (!subjectId || s.subject === subjectId);
      });
    },

    /* --- приглашения --- */
    inviteLink: function (teacherId, subjectId, studentId) {
      var base = new URL(".", global.location.href).href;
      var q = "?t=" + encodeURIComponent(teacherId) + "&s=" + encodeURIComponent(subjectId);
      if (studentId) q += "&i=" + encodeURIComponent(studentId);
      return base + "join.html" + q;
    },

    /* Персональное приглашение: преподаватель вписывает имя заранее,
       ученик появляется в списке сразу со статусом «приглашён». */
    invite: function (teacherId, subjectId, name, group) {
      var db = read();
      var subj = DB.subject(subjectId), tutor = DB.teacher(teacherId);
      if (!subj || !subj.variants.length || !tutor || tutor.subjects.indexOf(subjectId) < 0) return null;
      var st = {
        id: uid("s"), name: name, teacherId: teacherId, subject: subjectId,
        status: "invited", code: null, group: group || "", joinedAt: "только что"
      };
      db.students.push(st);
      write(db);
      return st;
    },

    /* --- вступление и оплата --- */
    join: function (teacherId, subjectId, name, inviteId) {
      var db = read(), st = null;
      var subj = DB.subject(subjectId), tutor = teacherId ? DB.teacher(teacherId) : null;
      if (!subj || !subj.variants.length || (teacherId && (!tutor || tutor.subjects.indexOf(subjectId) < 0))) return null;
      if (inviteId) {
        st = db.students.filter(function (s) { return s.id === inviteId; })[0] || null;
      }
      if (inviteId && (!st || st.teacherId !== teacherId || st.subject !== subjectId)) return null;
      if (st) {
        if (st.status === "paid") return st;
        if (name) st.name = name;                 // ученик уточняет своё имя
      } else {
        st = { id: uid("s"), name: name, teacherId: teacherId, subject: subjectId,
               status: "invited", code: null, group: "", joinedAt: "только что" };
        db.students.push(st);
      }
      write(db);
      return st;
    },

    pay: function (studentId) {
      var db = read();
      var st = db.students.filter(function (s) { return s.id === studentId; })[0];
      if (!st) return null;
      if (st.status === "paid") return st;
      var subj = db.subjects.filter(function (s) { return s.id === st.subject; })[0];
      var teacher = db.teachers.filter(function (t) { return t.id === st.teacherId; })[0];
      if (!subj || !subj.variants.length) return null;
      var sum = teacher ? subj.discount : subj.price;
      st.status = "paid";
      st.code = code(st.subject);
      st.joinedAt = "только что";
      db.payments.push({
        id: uid("p"), studentId: st.id, subject: st.subject, sum: sum,
        teacherId: st.teacherId,
        share: teacher ? Math.round(sum * teacher.percent / 100) : 0,
        paidOut: false, at: new Date().toISOString()
      });
      write(db);
      return st;
    },

    paymentsOf: function (teacherId) {
      return read().payments.filter(function (p) { return p.teacherId === teacherId; });
    },

    /* --- сессии (по одной на роль) --- */
    signIn: function (role, id) {
      var db = read();
      if (!db.session || typeof db.session.teacher === "undefined") db.session = { teacher: null, student: null };
      db.session[role] = id;
      write(db);
    },
    signOut: function (role) {
      var db = read();
      if (!db.session) db.session = { teacher: null, student: null };
      if (role) db.session[role] = null; else db.session = { teacher: null, student: null };
      write(db);
    },
    session: function () { return read().session; },
    currentStudent: function () {
      var s = read().session;
      return s && s.student ? DB.student(s.student) : null;
    },

    /* --- работы --- */
    submit: function (studentId, subjectId, work) {
      var db = read();
      var st = DB.student(studentId);
      if (!st || st.status !== "paid" || st.subject !== subjectId || !DB.subject(subjectId).variants.length) return null;
      var shortEssay = work.essay && (work.essay.match(/[A-Za-zА-Яа-яЁё0-9-]+/g) || []).length < 150;
      if (shortEssay) work.marks = { items: [], scores: { "К1":0,"К2":0,"К3":0,"К4":0,"К5":0,"К6":0 } };
      var sub = {
        id: uid("w"), studentId: studentId, subject: subjectId,
        variant: work.variant, part1: work.part1 || [],
        essay: work.essay || null, problem: work.problem || null,
        marks: work.marks || null,
        teacher: shortEssay ? {"К7":0,"К8":0,"К9":0,"К10":0} : {}, notes: [],
        status: !work.essay ? "done" : (st.teacherId ? "wait" : "saved"),
        at: new Date().toISOString(), date: "только что"
      };
      db.submissions.unshift(sub);
      write(db);
      return sub;
    },
    submissionsFor: function (teacherId, subjectId) {
      var db = read();
      var mine = {};
      db.students.forEach(function (s) { if (s.teacherId === teacherId) mine[s.id] = s; });
      return db.submissions
        .filter(function (w) { return mine[w.studentId] && (!subjectId || w.subject === subjectId); })
        .map(function (w) { w.student = mine[w.studentId]; return w; });
    },
    submissionsOf: function (studentId) {
      return read().submissions.filter(function (w) { return w.studentId === studentId; });
    },
    submission: function (id) {
      return read().submissions.filter(function (w) { return w.id === id; })[0];
    },
    saveSubmission: function (sub) {
      var db = read();
      for (var i = 0; i < db.submissions.length; i++) {
        if (db.submissions[i].id === sub.id) {
          var copy = {}; for (var k in sub) if (k !== "student") copy[k] = sub[k];
          db.submissions[i] = copy;
          break;
        }
      }
      write(db);
    }
  };

  global.addEventListener("storage", function (event) {
    if (event.key === KEY || event.key === null) {
      memory = null;
      global.dispatchEvent(new Event("demo-db-change"));
    }
  });
  global.DB = DB;
})(window);
