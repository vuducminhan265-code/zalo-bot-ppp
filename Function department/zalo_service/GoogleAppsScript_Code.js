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

function setupHeadersAndFormatting() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.setFrozenRows(7); // Khóa cố định từ dòng 7 trở lên (Dashboard & Headers)
  
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

  // 4. Cấu hình Dropdown Data Validation 4 trạng thái trên H8:H100 (Cột 8)
  var statusList = ["Chưa bắt đầu", "Đang thực hiện", "Đang sửa lại", "Đã hoàn thành"];
  var statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(statusList, true)
    .setAllowInvalid(false)
    .build();
  sheet.getRange("H8:H100").setDataValidation(statusRule);

  // 5. Cấu hình Conditional Formatting (Định dạng có điều kiện tự động đổi màu khi click chọn trên Cột H)
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

  // 6. Căn lề, Word Wrap và Kẻ bảng chuẩn công vụ cho toàn bộ vùng dữ liệu A8:O100
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
      
      // 2. Tự động gắn Dropdown 4 trạng thái nếu ô trạng thái (Cột H / Cột 8) chưa có
      var statusCell = sheet.getRange(editedRow, 8);
      if (!statusCell.getDataValidation()) {
        var statusList = ["Chưa bắt đầu", "Đang thực hiện", "Đang sửa lại", "Đã hoàn thành"];
        var statusRule = SpreadsheetApp.newDataValidation()
          .requireValueInList(statusList, true)
          .setAllowInvalid(false)
          .build();
        statusCell.setDataValidation(statusRule);
      }
      
      // 3. Nếu mới thêm task mà chưa chọn trạng thái, mặc định là "Đang thực hiện"
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
    
    // 1. Hỗ trợ trigger format và cài đặt bảng tự động từ xa
    if (postData.action === "formatSheet") {
      setupHeadersAndFormatting();
      return ContentService.createTextOutput(JSON.stringify({
        success: true,
        message: "Đã format và cấu hình lại Bảng giao việc Google Sheets 15 cột thành công!"
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
        
        var isMatch = false;
        var regex = new RegExp("^(?:task\\s*#?|t)?" + taskId + "\\b", "i");
        if (regex.test(name) || nameLower.indexOf("task " + taskId) !== -1 || nameLower.indexOf("task_" + taskId) !== -1 || nameLower.indexOf(taskId + "_") === 0 || nameLower.indexOf(taskId + " ") === 0 || nameLower.indexOf("task" + taskId) !== -1) {
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
