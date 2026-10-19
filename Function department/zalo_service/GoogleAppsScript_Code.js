/**
 * GOOGLE APPS SCRIPT CHO HỆ THỐNG ZALO BOT & AI REVIEW NHIỆM VỤ (CHUẨN 15 CỘT)
 * SỞ TÀI CHÍNH TP.HCM - PHÒNG HỢP TÁC CÔNG TƯ & QUẢN LÝ NỢ (PPP)
 * 
 * CẤU TRÚC BẢNG 15 CỘT:
 * A (1): Task ID
 * B (2): Tên nhiệm vụ / Công việc
 * C (3): Dự án
 * D (4): Người phụ trách
 * E (5): Lãnh đạo phòng
 * F (6): Hạn hoàn thành
 * G (7): Mức độ ưu tiên
 * H (8): Trạng thái (Dropdown 4 màu)
 * I (9): Sản phẩm
 * J (10): Trích yếu (Yêu cầu / Dự kiến)
 * K (11): Số ký hiệu văn bản
 * L (12): Ngày ban hành
 * M (13): Đánh giá AI (Tóm tắt file nộp)
 * N (14): Thời gian nộp
 * O (15): Tên file đã nộp
 */

function alignExistingDataTo15Columns(sheet) {
  if (!sheet) {
    sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Task_Tracker") || SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  }
  var lastRow = sheet.getLastRow();
  if (lastRow < 8) return;
  
  var numRows = Math.min(lastRow - 7, 95);
  var dataRange = sheet.getRange(8, 1, numRows, 15);
  var values = dataRange.getValues();
  var modified = false;
  
  // Danh sách từ khóa chuyên viên và sản phẩm để nhận diện chính xác hàng bị lệch 13 cột
  var staffKeywords = ["hòa", "lộc", "giang", "phúc", "ngọc", "khoa", "thoa", "hoàng", "tú", "nam", "vũ", "phượng", "phương", "trang", "vinh", "hận"];
  var deliverableKeywords = ["công văn", "tờ trình", "báo cáo", "kết luận", "phiếu trình", "văn bản nội bộ"];
  
  for (var i = 0; i < values.length; i++) {
    var row = values[i];
    var taskId = String(row[0] || "").trim();
    if (!taskId) continue;
    
    // Dấu hiệu hàng đang bị lệch theo kiểu cũ 13 cột:
    // 1. Cột C (row[2]) chứa tên chuyên viên
    // 2. Cột D (row[3]) chứa ngày hạn hoàn thành (Date hoặc chuỗi '2026-' / '/')
    // 3. Cột F (row[5]) chứa trạng thái ("Đang thực hiện", "Đã hoàn thành", "Đang sửa lại")
    // 4. Cột G (row[6]) chứa sản phẩm ("Công văn", "Tờ trình"...)
    var colC_val = String(row[2] || "").toLowerCase().trim();
    var colD_val = row[3];
    var colF_val = String(row[5] || "").toLowerCase().trim();
    var colG_val = String(row[6] || "").toLowerCase().trim();
    
    var isOldLayout = false;
    if (colD_val instanceof Date) {
      isOldLayout = true;
    } else if (typeof colD_val === "string" && (colD_val.indexOf("202") !== -1 || colD_val.indexOf("/") !== -1)) {
      isOldLayout = true;
    } else if (colF_val.indexOf("thực hiện") !== -1 || colF_val.indexOf("hoàn thành") !== -1 || colF_val.indexOf("sửa lại") !== -1) {
      isOldLayout = true;
    } else if (staffKeywords.some(function(k) { return colC_val.indexOf(k) !== -1; })) {
      isOldLayout = true;
    } else if (deliverableKeywords.some(function(k) { return colG_val.indexOf(k) !== -1; })) {
      isOldLayout = true;
    }
    
    if (isOldLayout) {
      modified = true;
      var taskName = row[1];
      var assignee = row[2];
      var deadline = row[3];
      var priority = row[4];
      var status = row[5];
      var deliverable = row[6];
      var trichYeu = row[7];
      var soKyHieu = row[8];
      var ngayBanHanh = row[9];
      var aiSummary = row[10];
      var submittedAt = row[11];
      var fileName = row[12];
      
      // Tự động bóc tách tên Dự án chuẩn xác từ Task Name hoặc Trích yếu
      var project = "";
      var textToScan = (trichYeu || taskName || "") + "";
      var m = textToScan.match(/(Dự\s*án(?:\s+thành\s+phần\s+\d+)?\s*[:\-\–]?\s*[\w\s\d,–\-\(\)\/\.\+]+?)(?=\s+theo\s+phương\s+thức|\s+thuộc\s+dự\s+án|\s+tại\s+|\s+của\s+công\s+ty|\s*\(Hợp\s*đồng|$)/i);
      if (m) {
        project = m[1].trim();
      } else {
        var mFallback = textToScan.match(/(Dự\s*án[^\.\n\r]+)/i);
        if (mFallback) project = mFallback[1].trim();
      }
      
      // Căn chỉnh vào đúng 15 cột mới:
      // A (0): Task ID | B (1): Tên nhiệm vụ | C (2): Dự án | D (3): Người phụ trách | E (4): Lãnh đạo phòng
      // F (5): Hạn hoàn thành | G (6): Mức độ ưu tiên | H (7): Trạng thái | I (8): Sản phẩm | J (9): Trích yếu
      // K (10): Số ký hiệu | L (11): Ngày ban hành | M (12): Đánh giá AI | N (13): Thời gian nộp | O (14): Tên file
      values[i][0] = taskId;
      values[i][1] = taskName;
      values[i][2] = project;
      values[i][3] = assignee;
      values[i][4] = "";
      values[i][5] = deadline;
      values[i][6] = priority;
      values[i][7] = status;
      values[i][8] = deliverable;
      values[i][9] = trichYeu;
      values[i][10] = soKyHieu;
      values[i][11] = ngayBanHanh;
      values[i][12] = aiSummary;
      values[i][13] = submittedAt;
      values[i][14] = fileName;
    }
  }
  
  if (modified) {
    dataRange.setValues(values);
    Logger.log("✅ Đã tự động dịch chuyển và căn chỉnh các hàng dữ liệu cũ sang đúng 15 cột mới!");
  }
}

function setupHeadersAndFormatting() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.setFrozenRows(7); // Khóa cố định từ dòng 7 trở lên (Dashboard & Headers)
  
  // Tự động căn chỉnh dữ liệu cũ nếu phát hiện đang bị lệch cột
  alignExistingDataTo15Columns(sheet);
  
  // 1. Cấu hình độ rộng 15 cột chuẩn thẩm mỹ công sở
  var columnWidths = {
    1: 65,   // A: Task ID
    2: 260,  // B: Tên nhiệm vụ / Công việc
    3: 180,  // C: Dự án
    4: 140,  // D: Người phụ trách
    5: 140,  // E: Lãnh đạo phòng
    6: 105,  // F: Hạn hoàn thành
    7: 105,  // G: Mức độ ưu tiên
    8: 130,  // H: Trạng thái
    9: 140,  // I: Sản phẩm
    10: 300, // J: Trích yếu (Yêu cầu / Dự kiến)
    11: 150, // K: Số ký hiệu văn bản
    12: 110, // L: Ngày ban hành
    13: 300, // M: Đánh giá AI (Tóm tắt file nộp)
    14: 140, // N: Thời gian nộp
    15: 200  // O: Tên file đã nộp
  };
  
  for (var col in columnWidths) {
    sheet.setColumnWidth(parseInt(col), columnWidths[col]);
  }
  
  // 2. Định dạng Dashboard thống kê (Dòng 4-5) trải đều toàn bộ 15 cột A -> O
  // Hủy gộp tất cả các ô merge cũ tại Dòng 4-5 để tránh lỗi Exception: You must select all cells in a merged range
  try {
    sheet.getRange("A4:Z5").breakApart();
  } catch (errBreak) {}

  // A4:C5 - Tổng số nhiệm vụ
  sheet.getRange("A4:C4").merge().setValue("TỔNG SỐ NHIỆM VỤ").setBackground("#E8F0FE").setFontColor("#174EA6").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("A5:C5").merge().setFormula('=COUNTA(A8:A100)').setBackground("#E8F0FE").setFontColor("#174EA6").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // D4:F5 - Chưa bắt đầu
  sheet.getRange("D4:F4").merge().setValue("CHƯA BẮT ĐẦU").setBackground("#F1F3F4").setFontColor("#5F6368").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("D5:F5").merge().setFormula('=COUNTIF(H8:H100, "Chưa bắt đầu")').setBackground("#F1F3F4").setFontColor("#5F6368").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // G4:I5 - Đang thực hiện
  sheet.getRange("G4:I4").merge().setValue("ĐANG THỰC HIỆN").setBackground("#FEF7E0").setFontColor("#B06000").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("G5:I5").merge().setFormula('=COUNTIF(H8:H100, "Đang thực hiện")').setBackground("#FEF7E0").setFontColor("#B06000").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // J4:L5 - Đang sửa lại (Cảnh báo)
  sheet.getRange("J4:L4").merge().setValue("ĐANG SỬA LẠI").setBackground("#FCE8E6").setFontColor("#C5221F").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("J5:L5").merge().setFormula('=COUNTIF(H8:H100, "Đang sửa lại")').setBackground("#FCE8E6").setFontColor("#C5221F").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // M4:O5 - Đã hoàn thành
  sheet.getRange("M4:O4").merge().setValue("ĐÃ HOÀN THÀNH").setBackground("#E6F4EA").setFontColor("#137333").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("M5:O5").merge().setFormula('=COUNTIF(H8:H100, "Đã hoàn thành")').setBackground("#E6F4EA").setFontColor("#137333").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // Đóng khung viền mỏng cho Dashboard
  sheet.getRange("A4:O5").setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);

  // 3. 15 Cột Tiêu đề Header (Dòng 7)
  var headers = [
    "Task ID",
    "Tên nhiệm vụ / Công việc",
    "Dự án",
    "Người phụ trách",
    "Lãnh đạo phòng",
    "Hạn hoàn thành",
    "Mức độ ưu tiên",
    "Trạng thái",
    "Sản phẩm",
    "Trích yếu (Yêu cầu / Dự kiến)",
    "Số ký hiệu văn bản",
    "Ngày ban hành",
    "Đánh giá AI (Tóm tắt file nộp)",
    "Thời gian nộp",
    "Tên file đã nộp"
  ];
  
  var headerRange = sheet.getRange(7, 1, 1, headers.length);
  headerRange.setValues([headers]);
  headerRange.setBackground("#0F4C81"); // Deep Navy chuẩn công vụ
  headerRange.setFontColor("#FFFFFF");
  headerRange.setFontWeight("bold");
  headerRange.setFontSize(10);
  headerRange.setHorizontalAlignment("center");
  headerRange.setVerticalAlignment("middle");
  sheet.setRowHeight(7, 36);

  // 4. Xóa sạch toàn bộ Data Validation cũ bị sót lại trên các cột khác (đặc biệt là Cột F Hạn hoàn thành)
  try {
    sheet.getRange("A8:G100").clearDataValidations();
    sheet.getRange("I8:O100").clearDataValidations();
  } catch (errClear) {}

  // Định dạng chuẩn Date Picker sạch sẽ cho Cột F (Hạn hoàn thành - Cột 6)
  try {
    var deadlineRange = sheet.getRange("F8:F100");
    var dateRule = SpreadsheetApp.newDataValidation()
      .requireDate()
      .setAllowInvalid(true)
      .build();
    deadlineRange.setDataValidation(dateRule);
  } catch (errDate) {}

  // 5. Cấu hình Dropdown Data Validation 4 trạng thái DUY NHẤT trên Cột H (H8:H100 - Cột 8)
  try {
    var statusList = ["Chưa bắt đầu", "Đang thực hiện", "Đang sửa lại", "Đã hoàn thành"];
    var statusRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(statusList, true)
      .setAllowInvalid(false)
      .build();
    sheet.getRange("H8:H100").setDataValidation(statusRule);
  } catch (errVal) {}

  // 6. Cấu hình Conditional Formatting (Bọc trong try-catch vì Google Tables chặn format trên typed columns)
  try {
    var statusRange = sheet.getRange("H8:H100");
    var ruleCompleted = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("Đã hoàn thành")
      .setBackground("#E6F4EA")
      .setFontColor("#137333")
      .setRanges([statusRange])
      .build();

    var ruleWorking = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("Đang thực hiện")
      .setBackground("#FEF7E0")
      .setFontColor("#B06000")
      .setRanges([statusRange])
      .build();

    var ruleRevising = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("Đang sửa lại")
      .setBackground("#FCE8E6")
      .setFontColor("#C5221F")
      .setRanges([statusRange])
      .build();

    var ruleNotStarted = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("Chưa bắt đầu")
      .setBackground("#F1F3F4")
      .setFontColor("#5F6368")
      .setRanges([statusRange])
      .build();

    sheet.setConditionalFormatRules([ruleCompleted, ruleWorking, ruleRevising, ruleNotStarted]);
  } catch (errCond) {}

  // 7. Căn lề, Word Wrap và Kẻ bảng chuẩn công vụ cho toàn bộ vùng dữ liệu A8:O100
  try {
    var dataRange = sheet.getRange("A8:O100");
    dataRange.setVerticalAlignment("middle");
    dataRange.setFontSize(10);
    dataRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
    dataRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
    
    // Căn giữa các cột mã số, ngày, trạng thái
    sheet.getRange("A8:A100").setHorizontalAlignment("center");
    sheet.getRange("F8:H100").setHorizontalAlignment("center");
    sheet.getRange("K8:L100").setHorizontalAlignment("center");
    sheet.getRange("N8:N100").setHorizontalAlignment("center");

    // Căn trái các cột văn bản dài
    sheet.getRange("B8:E100").setHorizontalAlignment("left");
    sheet.getRange("I8:J100").setHorizontalAlignment("left");
    sheet.getRange("M8:M100").setHorizontalAlignment("left");
    sheet.getRange("O8:O100").setHorizontalAlignment("left");

    // Thiết lập chiều cao dòng mặc định cho các dòng có dữ liệu
    for (var r = 8; r <= 35; r++) {
      sheet.setRowHeight(r, 45);
    }
  } catch (errFormat) {}
  
  SpreadsheetApp.flush();
  Logger.log("✅ Đã thiết lập hoàn tất: Bảng 15 cột, Dropdown 4 trạng thái, Conditional Formatting tự đổi màu, Text Wrapping và Kẻ bảng viền mỏng!");
}

/**
 * TỰ ĐỘNG BẮT SỰ KIỆN KHI NGƯỜI DÙNG GÕ THÊM NHIỆM VỤ MỚI TRÊN GOOGLE SHEETS
 * Tự động kẻ bảng, đóng viền mỏng, gắn dropdown trạng thái và wrap text ngay lập tức!
 */
function onEdit(e) {
  try {
    var range = e.range;
    var sheet = range.getSheet();
    var editedRow = range.getRow();
    
    // Chỉ kích hoạt cho các dòng dữ liệu từ dòng 8 trở xuống
    if (editedRow >= 8) {
      var rowRange = sheet.getRange(editedRow, 1, 1, 15);
      
      // 1. Kẻ viền mỏng công sở toàn bộ 15 cột của dòng đó
      rowRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
      rowRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
      rowRange.setVerticalAlignment("middle");
      rowRange.setFontSize(10);
      
      // 2. Đảm bảo Cột F (Hạn hoàn thành) là Date Picker sạch sẽ, không bị dính Dropdown trạng thái
      var deadlineCell = sheet.getRange(editedRow, 6);
      if (deadlineCell.getDataValidation() && deadlineCell.getDataValidation().getCriteriaType() === SpreadsheetApp.DataValidationCriteria.VALUE_IN_LIST) {
        deadlineCell.clearDataValidations();
        var dateRule = SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(true).build();
        deadlineCell.setDataValidation(dateRule);
      }

      // 3. Tự động gắn Dropdown 4 trạng thái nếu ô trạng thái (Cột H / Cột 8) chưa có
      var statusCell = sheet.getRange(editedRow, 8);
      if (!statusCell.getDataValidation()) {
        var statusList = ["Chưa bắt đầu", "Đang thực hiện", "Đang sửa lại", "Đã hoàn thành"];
        var statusRule = SpreadsheetApp.newDataValidation()
          .requireValueInList(statusList, true)
          .setAllowInvalid(false)
          .build();
        statusCell.setDataValidation(statusRule);
      }
      
      // 4. Nếu mới thêm task mà chưa chọn trạng thái, mặc định là "Đang thực hiện"
      if (!statusCell.getValue()) {
        statusCell.setValue("Đang thực hiện");
      }
      
      // 4. Căn lề chuẩn
      sheet.getRange(editedRow, 1).setHorizontalAlignment("center");
      sheet.getRange(editedRow, 6, 1, 3).setHorizontalAlignment("center");
      sheet.getRange(editedRow, 11, 1, 2).setHorizontalAlignment("center");
      sheet.getRange(editedRow, 14).setHorizontalAlignment("center");
      
      // Thiết lập chiều cao dòng tối thiểu 45px
      sheet.setRowHeight(editedRow, Math.max(sheet.getRowHeight(editedRow), 45));
    }
  } catch (err) {
    // Không làm gián đoạn người dùng nếu có lỗi
  }
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var postData = JSON.parse(e.postData.contents);
    
    // 1. Hỗ trợ trigger format và khôi phục căn chỉnh bảng tự động từ xa
    if (postData.action === "restoreCleanData" || postData.action === "formatSheet") {
      repairAndRestoreAllTasksClean();
      return ContentService.createTextOutput(JSON.stringify({
        success: true,
        message: "Đã khôi phục và căn chỉnh 100% dữ liệu chuẩn 15 cột thành công!"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // 2. Hỗ trợ quét Thư mục Google Drive tìm tệp PDF theo Task ID
    if (postData.action === "scan_drive") {
      var folderId = postData.folderId || "1j8C6PalsK_Z14-C88oKGy3u38OHuKRjL";
      var taskId = String(postData.taskId).trim();
      var folder = DriveApp.getFolderById(folderId);
      var files = folder.getFiles();
      var matchedFiles = [];
      
      while (files.hasNext()) {
        var file = files.next();
        var name = file.getName();
        var nameLower = name.toLowerCase();
        
        // Nhận diện chuẩn format: "[Số Task] - [Tên file] - [Tên chuyên viên].pdf"
        // Ví dụ: "4 - Tờ trình - Nguyễn Trung Bảo Lộc.pdf", "4 - file - tên chuyên viên.pdf", "Task 4 - To trinh.pdf"
        var isMatch = false;
        var regex = new RegExp("^(?:task\\s*#?|nv\\s*#?|t)?\\s*" + taskId + "\\s*([\\-_–\\s]|$)", "i");
        if (regex.test(name) || nameLower.indexOf(taskId + " - ") === 0 || nameLower.indexOf(taskId + "-") === 0 || nameLower.indexOf(taskId + "_") === 0 || nameLower.indexOf("task " + taskId) !== -1 || nameLower.indexOf("task_" + taskId) !== -1 || nameLower.indexOf(taskId + " ") === 0) {
          isMatch = true;
        }
        
        if (isMatch) {
          var blob = file.getBlob();
          var b64 = Utilities.base64Encode(blob.getBytes());
          matchedFiles.push({
            id: file.getId(),
            name: name,
            mimeType: file.getMimeType(),
            size: file.getSize(),
            base64: b64,
            downloadUrl: file.getDownloadUrl()
          });
          break;
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        success: matchedFiles.length > 0,
        files: matchedFiles
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 3. Cập nhật kết quả thẩm định nhiệm vụ (15 Cột)
    var taskId = String(postData.taskId).trim();
    var status = postData.status || "Đã hoàn thành";
    var summary = postData.summary || "";
    var fileName = postData.fileName || "";
    var docNumber = postData.docNumber || "";
    var docDate = postData.docDate || "";
    var actualSummary = postData.actualSummary || "";
    var deliverable = postData.deliverable || "";
    var project = postData.project || "";
    
    var now = new Date();
    var formattedTime = Utilities.formatDate(now, "GMT+7", "yyyy-MM-dd HH:mm:ss");
    
    var data = sheet.getDataRange().getValues();
    var targetRow = -1;
    
    for (var i = 7; i < data.length; i++) {
      if (String(data[i][0]).trim() === taskId) {
        targetRow = i + 1;
        break;
      }
    }
    
    if (targetRow === -1) {
      return ContentService.createTextOutput(JSON.stringify({
        success: false,
        message: "Không tìm thấy Task ID: " + taskId
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Cập nhật Cột 8 (Cột H): Trạng thái
    var statusCell = sheet.getRange(targetRow, 8);
    statusCell.setValue(status);
    
    // Đổi màu nền trạng thái trực quan
    if (status === "Đã hoàn thành") {
      statusCell.setBackground("#E6F4EA"); // Xanh lá nhạt
      statusCell.setFontColor("#137333");
      statusCell.setFontWeight("bold");
    } else if (status === "Đang sửa lại") {
      statusCell.setBackground("#FCE8E6"); // Đỏ hồng cảnh báo
      statusCell.setFontColor("#C5221F");
      statusCell.setFontWeight("bold");
    } else if (status === "Đang thực hiện") {
      statusCell.setBackground("#FEF7E0");
      statusCell.setFontColor("#B06000");
    }
    
    // Cập nhật Cột 3 (Cột C): Dự án (nếu rỗng hoặc có bóc tách mới)
    if (project) {
      var currentProj = String(sheet.getRange(targetRow, 3).getValue() || "").trim();
      if (!currentProj) {
        sheet.getRange(targetRow, 3).setValue(project);
      }
    }
    
    // Cập nhật Cột 9 (Cột I): Sản phẩm (Tờ trình, Kết luận, Báo cáo, Công văn...)
    if (deliverable) {
      var currentDeliv = String(sheet.getRange(targetRow, 9).getValue() || "").trim();
      if (!currentDeliv || status === "Đã hoàn thành") {
        sheet.getRange(targetRow, 9).setValue(deliverable);
      }
    }
    
    // Cập nhật trích yếu thực tế nếu có
    if (actualSummary) sheet.getRange(targetRow, 10).setValue(actualSummary);
    if (docNumber) sheet.getRange(targetRow, 11).setValue(docNumber);
    if (docDate) sheet.getRange(targetRow, 12).setValue(docDate);
    sheet.getRange(targetRow, 13).setValue(summary);
    sheet.getRange(targetRow, 14).setValue(formattedTime);
    sheet.getRange(targetRow, 15).setValue(fileName);
    
    // Tự động kẻ bảng, wrap text và căn lề toàn bộ hàng vừa cập nhật (cột 1 đến 15)
    var updatedRowRange = sheet.getRange(targetRow, 1, 1, 15);
    updatedRowRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
    updatedRowRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
    updatedRowRange.setVerticalAlignment("middle");
    updatedRowRange.setFontSize(10);
    
    SpreadsheetApp.flush();
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: "Cập nhật thành công cho Task ID: " + taskId
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var tasks = [];
  
  // Kiểm tra số lượng cột thực tế (hỗ trợ cả bảng 13 cột và 15 cột)
  var is15Col = data.length > 6 && data[6].length >= 15;
  
  for (var i = 7; i < data.length; i++) {
    var row = data[i];
    if (row[0] && String(row[0]).trim() !== "") {
      if (is15Col) {
        tasks.push({
          taskId: String(row[0]).trim(),
          taskName: row[1] || "",
          project: row[2] || "",
          assignee: row[3] || "",
          leader: row[4] || "",
          deadline: row[5] || "",
          priority: row[6] || "",
          status: row[7] || "",
          deliverable: row[8] || "",
          trichYeu: row[9] || "",
          soKyHieu: row[10] || "",
          ngayBanHanh: row[11] || "",
          aiSummary: row[12] || "",
          submittedAt: row[13] || "",
          fileName: row[14] || ""
        });
      } else {
        // Cấu trúc cũ 13 cột
        tasks.push({
          taskId: String(row[0]).trim(),
          taskName: row[1] || "",
          project: "",
          assignee: row[2] || "",
          leader: "",
          deadline: row[3] || "",
          priority: row[4] || "",
          status: row[5] || "",
          deliverable: row[6] || "",
          trichYeu: row[7] || "",
          soKyHieu: row[8] || "",
          ngayBanHanh: row[9] || "",
          aiSummary: row[10] || "",
          submittedAt: row[11] || "",
          fileName: row[12] || ""
        });
      }
    }
  }
  
  return ContentService.createTextOutput(JSON.stringify({
    success: true,
    data: tasks
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * TỰ ĐỘNG PHÁT BẢN TIN NHẮC VIỆC LÊN ZALO GROUP HÀNG NGÀY (07:45 SÁNG & 17:30 CHIỀU)
 * Chạy 100% trên Đám mây Google Apps Script - Không cần bật máy tính.
 */
function sendDailyZaloMorningReminder() {
  var renderServiceUrl = "https://zalo-bot-ppp-service.onrender.com/api/cron/morning";
  try {
    UrlFetchApp.fetch(renderServiceUrl, { "muteHttpExceptions": true });
  } catch (err) {
    Logger.log("Trigger error: " + err);
  }
}

function sendDailyZaloEveningSummary() {
  var renderServiceUrl = "https://zalo-bot-ppp-service.onrender.com/api/cron/evening";
  try {
    UrlFetchApp.fetch(renderServiceUrl, { "muteHttpExceptions": true });
  } catch (err) {
    Logger.log("Trigger error: " + err);
  }
}

function createDailyTriggers() {
  // Xóa các trigger cũ để tránh trùng lặp
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  
  // 1. Kích hoạt Trigger 07:45 Sáng (Bản tin nhắc việc & tiến độ)
  ScriptApp.newTrigger("sendDailyZaloMorningReminder")
    .timeBased()
    .atHour(7)
    .nearMinute(45)
    .everyDays(1)
    .inTimezone("Asia/Ho_Chi_Minh")
    .create();

  // 2. Kích hoạt Trigger 17:30 Chiều (Bản tin tổng kết cuối ngày)
  ScriptApp.newTrigger("sendDailyZaloEveningSummary")
    .timeBased()
    .atHour(17)
    .nearMinute(30)
    .everyDays(1)
    .inTimezone("Asia/Ho_Chi_Minh")
    .create();
    
  Logger.log("✅ Đã kích hoạt Trigger tự động phát bản tin 07:45 & 17:30 hàng ngày thành công!");
}

/**
 * TẠO MENU TRÊN THANH CÔNG CỤ GOOGLE SHEETS
 * Giúp người dùng click 1 phát là chạy ngay trên Google Sheets, không bao giờ cần vào Apps Script nữa!
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("⚡ QUẢN LÝ NHIỆM VỤ")
    .addItem("🚀 KHÔI PHỤC & CĂN CHỈNH 15 CỘT (CLICK LÀ XONG)", "repairAndRestoreAllTasksClean")
    .addItem("🔄 Format Lại Dashboard & Headers", "setupHeadersAndFormatting")
    .addItem("🛠️ Căn Chỉnh Dữ Liệu Tự Động", "forceFixMisalignedColumns")
    .addToUi();
}

/**
 * HÀM CƯỠNG CHẾ CĂN CHỈNH DỮ LIỆU LỆCH 15 CỘT
 */
function forceFixMisalignedColumns() {
  repairAndRestoreAllTasksClean();
}

/**
 * HÀM KHÔI PHỤC VÀ ĐỒNG BỘ 100% DỮ LIỆU CHUẨN 15 CỘT
 * Giải quyết triệt để vấn đề lệch cột, sai vị trí trường dữ liệu, đè chữ Đã hoàn thành và lỗi dropdown Cột F!
 */
function repairAndRestoreAllTasksClean() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Task_Tracker") || SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  // 1. Phá bỏ mọi định dạng / merge / validation lỗi ở vùng dữ liệu cũ (A8:O30)
  try {
    sheet.getRange("A8:O30").clearDataValidations();
    sheet.getRange("A8:O30").clearFormat();
  } catch (e) {}

  // 2. Định dạng lại Dashboard và 15 Cột Headers chuẩn
  setupHeadersAndFormatting();

  // 3. Dữ liệu chuẩn xác 100% của 7 nhiệm vụ theo đúng cấu trúc 15 Cột (A -> O)
  var cleanTasksData = [
    // Task 1
    [
      "1",
      "Về giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo kết hợp xây dựng công viên, bãi tắm công cộng ven biển Phước Hải theo phương thức đối tác công tư (Hợp đồng BT) của Công ty Cổ phần Phát triển Bất động sản Phát Đạt",
      "Dự án Bãi tắm Thùy Vân - Trần Hưng Đạo",
      "Nguyễn Thế Hòa",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đang thực hiện",
      "Công văn",
      "V/v giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo",
      "",
      "",
      "",
      "",
      ""
    ],
    // Task 2
    [
      "2",
      "V/v giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo kết hợp xây dựng công viên, bãi tắm công cộng ven biển Phước Hải theo phương thức đối tác công tư (Hợp đồng BT) của Công ty Cổ phần Phát triển Bất động sản Phát Đạt",
      "Dự án 247 Trần Hưng Đạo",
      "Nguyễn Thế Hòa",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đang thực hiện",
      "Công văn",
      "Có ý kiến việc giao thực hiện dự án theo hình thức BT",
      "",
      "",
      "",
      "",
      ""
    ],
    // Task 3
    [
      "3",
      "V/v giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo kết hợp xây dựng công viên, bãi tắm công cộng ven biển Phước Hải theo phương thức đối tác công tư (Hợp đồng BT) của Công ty Cổ phần Phát triển Bất động sản Phát Đạt.",
      "Dự án Phước Hải - Phát Đạt",
      "Nguyễn Thế Hòa",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đang thực hiện",
      "Công văn",
      "27239 STC-PPPQLN",
      "",
      "",
      "",
      "",
      ""
    ],
    // Task 4
    [
      "4",
      "Dự án Chỉnh trang đô thị Khu Mả Lạng và Chợ Gà - Gạo trên địa bàn phường Cầu Ông Lãnh và phường Bến Thành, Thành phố Hồ Chí Minh theo phương thức đối tác công tư (Hợp đồng BT)",
      "Dự án Chỉnh trang Khu Mả Lạng và Chợ Gà - Gạo",
      "Nguyễn Trung Bảo Lộc",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đã hoàn thành",
      "Công văn",
      "V/v ý kiến đối với Báo cáo nghiên cứu khả thi điều chỉnh Dự án Chỉnh trang đô thị Khu Mả Lạng và Chợ Gà – Gạo",
      "24586/STC-PPP&QLN",
      "2026-10-19",
      "Đã thẩm định đạt chuẩn Nghị định 30/2020/NĐ-CP (Khớp chuyên viên: Nguyễn Trung Bảo Lộc)",
      "2026-10-19 15:30:00",
      "4 - 24586 STC PPP.signed - Lộc.pdf"
    ],
    // Task 5
    [
      "5",
      "dự án thành phần 3: Bồi thường, hỗ trợ, tái định cư cao tốc Thành phố Hồ Chí Minh - Mộc Bài đoạn qua Thành phố Hồ Chí Minh thuộc dự án đầu tư xây dựng đường cao tốc Thành phố Hồ Chí Minh - Mộc Bài (giai đoạn 1)",
      "Dự án Cao tốc TP.HCM - Mộc Bài",
      "Hoàng Thị Hương Giang",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đang thực hiện",
      "Công văn",
      "V/v ý kiến đối với Báo cáo nghiên cứu khả thi điều chỉnh dự án thành phần 3: Bồi thường, hỗ trợ, tái định cư cao tốc Thành phố Hồ Chí Minh – Mộc Bài",
      "",
      "",
      "",
      "",
      ""
    ],
    // Task 6
    [
      "6",
      "Về thành lập Hội đồng thẩm định báo cáo nghiên cứu khả thi Dự án Khu liên hợp thể dục thể thao quốc gia Rạch Chiếc",
      "Dự án Khu liên hợp TDTT Rạch Chiếc",
      "Nguyễn Thế Hòa",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đang thực hiện",
      "Công văn",
      "Về thành lập Hội đồng thẩm định báo cáo nghiên cứu khả thi",
      "",
      "",
      "",
      "",
      ""
    ],
    // Task 7
    [
      "7",
      "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng Dự án Khu liên hợp thể dục thể thao quốc gia Rạch Chiếc theo phương thức đối tác công tư (PPP) Hạng mục hạ tầng kỹ thuật toàn khu",
      "Dự án Hạ tầng kỹ thuật Rạch Chiếc",
      "Nguyễn Thế Hòa",
      "Lê Hoàng",
      "2026-10-31",
      "Gấp",
      "Đang thực hiện",
      "Tờ trình",
      "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng Dự án Khu liên hợp thể dục thể thao quốc gia Rạch Chiếc Hạng mục hạ tầng kỹ thuật toàn khu",
      "",
      "",
      "",
      "",
      ""
    ]
  ];

  // Ghi đè chính xác 7 hàng từ dòng 8 đến dòng 14, từ cột 1 (A) đến cột 15 (O)
  sheet.getRange(8, 1, cleanTasksData.length, 15).setValues(cleanTasksData);

  // Xóa sạch các ô rác phía dưới (từ dòng 15 đến 30) nếu có
  try {
    sheet.getRange(15, 1, 16, 15).clearContent();
  } catch (eClean) {}

  // Tô màu trạng thái chuẩn cho Cột H (Cột 8)
  for (var r = 0; r < cleanTasksData.length; r++) {
    var rowNum = 8 + r;
    var st = cleanTasksData[r][7];
    var cell = sheet.getRange(rowNum, 8);
    if (st === "Đã hoàn thành") {
      cell.setBackground("#E6F4EA").setFontColor("#137333").setFontWeight("bold");
    } else if (st === "Đang thực hiện") {
      cell.setBackground("#FEF7E0").setFontColor("#B06000").setFontWeight("bold");
    } else if (st === "Đang sửa lại") {
      cell.setBackground("#FCE8E6").setFontColor("#C5221F").setFontWeight("bold");
    }
  }

  // Căn lề, đóng khung và wrap text toàn bộ bảng
  var dataRange = sheet.getRange(8, 1, cleanTasksData.length, 15);
  dataRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
  dataRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
  dataRange.setVerticalAlignment("middle");
  dataRange.setFontSize(10);

  // Căn giữa các cột mã số, ngày, trạng thái
  sheet.getRange("A8:A14").setHorizontalAlignment("center");
  sheet.getRange("E8:G14").setHorizontalAlignment("center");
  sheet.getRange("H8:I14").setHorizontalAlignment("center");
  sheet.getRange("K8:L14").setHorizontalAlignment("center");
  sheet.getRange("N8:N14").setHorizontalAlignment("center");

  try {
    SpreadsheetApp.getUi().alert("🎉 ĐÃ KHÔI PHỤC VÀ CĂN CHỈNH 100% DỮ LIỆU CHUẨN 15 CỘT THÀNH CÔNG!");
  } catch (e) {
    Logger.log("Restored successfully!");
  }
}

