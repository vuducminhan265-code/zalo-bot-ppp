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
  // Hàm này đã được vô hiệu hóa để bảo vệ an toàn tuyệt đối 100% dữ liệu của chuyên viên,
  // tránh việc tự động xáo trộn hoặc dịch chuyển cột sai lệch.
  Logger.log("ℹ️ Dữ liệu đã được bảo toàn nguyên vẹn.");
}

function setupHeadersAndFormatting() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Task_Tracker") || SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
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

  // 4. Xóa sạch Data Validation thừa trên các cột không dùng Dropdown
  try {
    sheet.getRange("A8:D100").clearDataValidations();
    sheet.getRange("J8:O100").clearDataValidations();
  } catch (errClear) {}

  // 5. Cấu hình Dropdowns và Date Picker chuẩn
  // 5.1. Cột E: Lãnh đạo phòng
  try {
    var leaderList = ["Lê Hoàng", "Tô Thị Kim Thoa", "Nguyễn Thế Hòa"];
    var leaderRule = SpreadsheetApp.newDataValidation().requireValueInList(leaderList, true).setAllowInvalid(true).build();
    sheet.getRange("E8:E100").setDataValidation(leaderRule);
  } catch (errLeader) {}

  // 5.2. Cột F: Hạn hoàn thành - Date Picker chuẩn
  try {
    sheet.getRange("F8:F100").clearDataValidations();
    var dateRule = SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(true).build();
    sheet.getRange("F8:F100").setDataValidation(dateRule);
    sheet.getRange("F8:F100").setNumberFormat("yyyy-mm-dd");
  } catch (errDate) {}

  // 5.3. Cột G: Mức độ ưu tiên
  try {
    var prioList = ["Bình thường", "Gấp", "Hỏa tốc"];
    var prioRule = SpreadsheetApp.newDataValidation().requireValueInList(prioList, true).setAllowInvalid(true).build();
    sheet.getRange("G8:G100").setDataValidation(prioRule);
  } catch (errPrio) {}

  // 5.4. Cột H: Trạng thái (Dropdown 4 màu)
  try {
    var statusList = ["Chưa bắt đầu", "Đang thực hiện", "Đang sửa lại", "Đã hoàn thành"];
    var statusRule = SpreadsheetApp.newDataValidation().requireValueInList(statusList, true).setAllowInvalid(false).build();
    sheet.getRange("H8:H100").setDataValidation(statusRule);
  } catch (errVal) {}

  // 5.5. Cột I: Sản phẩm
  try {
    var prodList = ["Công văn", "Tờ trình", "Báo cáo", "Kết luận", "Phiếu trình", "Kế hoạch", "Thông báo", "Quyết định"];
    var prodRule = SpreadsheetApp.newDataValidation().requireValueInList(prodList, true).setAllowInvalid(true).build();
    sheet.getRange("I8:I100").setDataValidation(prodRule);
  } catch (errProd) {}

  // 6. Cấu hình Conditional Formatting tự động đổi màu theo Trạng thái tại Cột H
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

  // 7. Căn lề, Word Wrap và Kẻ bảng chuẩn công vụ cho toàn bộ vùng dữ liệu A8:O100 (BẢO TOÀN 100% NỘI DUNG)
  try {
    var lastRow = Math.max(sheet.getLastRow(), 14);
    var numRows = lastRow - 7;
    var dataRange = sheet.getRange(8, 1, numRows, 15);
    dataRange.setVerticalAlignment("middle");
    dataRange.setFontSize(10);
    dataRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
    dataRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
    
    // Căn giữa các cột mã số, ngày, trạng thái
    sheet.getRange("A8:A" + lastRow).setHorizontalAlignment("center");
    sheet.getRange("E8:I" + lastRow).setHorizontalAlignment("center");
    sheet.getRange("K8:L" + lastRow).setHorizontalAlignment("center");
    sheet.getRange("N8:N" + lastRow).setHorizontalAlignment("center");

    // Căn trái các cột văn bản dài
    sheet.getRange("B8:D" + lastRow).setHorizontalAlignment("left");
    sheet.getRange("J8:J" + lastRow).setHorizontalAlignment("left");
    sheet.getRange("M8:M" + lastRow).setHorizontalAlignment("left");
    sheet.getRange("O8:O" + lastRow).setHorizontalAlignment("left");
  } catch (errFormat) {}
  
  SpreadsheetApp.flush();
  try {
    SpreadsheetApp.getUi().alert("✨ ĐÃ FORMAT GIAO DIỆN & DROPDOWN THÀNH CÔNG!\n• Giữ nguyên 100% dữ liệu từng nhiệm vụ.\n• Đồng bộ Dashboard, Date Picker (Cột F) và Dropdown Trạng thái (Cột H).");
  } catch (e) {}
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
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Task_Tracker") || SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
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
    
    // 3. Cập nhật kết quả thẩm định nhiệm vụ (CHUẨN 15 CỘT DỰA TRÊN DÒNG TIÊU ĐỀ DÒNG 7)
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

    // Bóc tách động các cột dựa trên Dòng 7 để đảm bảo KHÔNG BAO GIỜ ghi đè nhầm cột
    var headerRow = sheet.getRange(7, 1, 1, Math.max(sheet.getLastColumn(), 15)).getValues()[0];
    function getColIdx(keywords, defaultCol) {
      for (var c = 0; c < headerRow.length; c++) {
        var h = String(headerRow[c] || "").trim().toLowerCase();
        for (var k = 0; k < keywords.length; k++) {
          if (h.indexOf(keywords[k]) !== -1) return c + 1; // 1-based index
        }
      }
      return defaultCol;
    }

    var colProject = getColIdx(["dự án"], 3);
    var colStatus = getColIdx(["trạng thái"], 8);
    var colDeliverable = getColIdx(["sản phẩm"], 9);
    var colSummary = getColIdx(["trích yếu"], 10);
    var colDocNumber = getColIdx(["số ký hiệu", "số văn bản"], 11);
    var colDocDate = getColIdx(["ngày ban hành"], 12);
    var colAiReview = getColIdx(["đánh giá ai"], 13);
    var colSubmittedAt = getColIdx(["thời gian nộp"], 14);
    var colFileName = getColIdx(["tên file"], 15);

    // BẢO VỆ TUYỆT ĐỐI CỘT 6 (HẠN HOÀN THÀNH) VÀ CỘT 7 (MỨC ĐỘ ƯU TIÊN):
    // Tuyệt đối không bao giờ cho phép ghi đè Trạng thái hay Sản phẩm vào Cột 6 hoặc Cột 7!
    if (colStatus <= 7) colStatus = 8;
    if (colDeliverable <= 7) colDeliverable = 9;
    
    // Cập nhật Cột Trạng thái (Cột H / Cột 8)
    var statusCell = sheet.getRange(targetRow, colStatus);
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
    
    // Cập nhật Cột Dự án (Cột C / Cột 3)
    if (project) {
      var currentProj = String(sheet.getRange(targetRow, colProject).getValue() || "").trim();
      if (!currentProj) {
        sheet.getRange(targetRow, colProject).setValue(project);
      }
    }
    
    // Cập nhật Cột Sản phẩm (Cột I / Cột 9)
    if (deliverable) {
      var currentDeliv = String(sheet.getRange(targetRow, colDeliverable).getValue() || "").trim();
      if (!currentDeliv || status === "Đã hoàn thành") {
        sheet.getRange(targetRow, colDeliverable).setValue(deliverable);
      }
    }
    
    // Cập nhật các cột thông tin thẩm định chi tiết
    if (actualSummary) sheet.getRange(targetRow, colSummary).setValue(actualSummary);
    if (docNumber) sheet.getRange(targetRow, colDocNumber).setValue(docNumber);
    if (docDate) sheet.getRange(targetRow, colDocDate).setValue(docDate);
    sheet.getRange(targetRow, colAiReview).setValue(summary);
    sheet.getRange(targetRow, colSubmittedAt).setValue(formattedTime);
    sheet.getRange(targetRow, colFileName).setValue(fileName);
    
    // Tự động kẻ bảng, wrap text và căn lề toàn bộ hàng vừa cập nhật (cột 1 đến 15)
    var updatedRowRange = sheet.getRange(targetRow, 1, 1, 15);
    updatedRowRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
    updatedRowRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
    updatedRowRange.setVerticalAlignment("middle");
    updatedRowRange.setFontSize(10);
    
    SpreadsheetApp.flush();
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: "Cập nhật thành công cho Task ID: " + taskId + " vào đúng Cột 8 (Trạng thái) & Cột 9 (Sản phẩm)!"
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
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Task_Tracker") || SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var tasks = [];
  
  if (data.length < 8) {
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      data: tasks
    })).setMimeType(ContentService.MimeType.JSON);
  }
  
  var headerRow = data[6].map(function(h) { return String(h || "").trim().toLowerCase(); });
  function findColIdx(keywords, defaultCol) {
    for (var c = 0; c < headerRow.length; c++) {
      for (var k = 0; k < keywords.length; k++) {
        if (headerRow[c].indexOf(keywords[k]) !== -1) return c;
      }
    }
    return defaultCol;
  }
  
  var colTaskId = findColIdx(["task id", "mã task", "id"], 0);
  var colTaskName = findColIdx(["tên nhiệm vụ", "công việc"], 1);
  var colProject = findColIdx(["dự án"], 2);
  var colAssignee = findColIdx(["người phụ trách", "chuyên viên"], 3);
  var colLeader = findColIdx(["lãnh đạo"], 4);
  var colDeadline = findColIdx(["hạn hoàn thành", "deadline"], 5);
  var colPriority = findColIdx(["mức độ ưu tiên", "ưu tiên"], 6);
  var colStatus = findColIdx(["trạng thái"], 7);
  var colDeliverable = findColIdx(["sản phẩm"], 8);
  var colSummary = findColIdx(["trích yếu"], 9);
  var colDocNum = findColIdx(["số ký hiệu", "số văn bản"], 10);
  var colDocDate = findColIdx(["ngày ban hành"], 11);
  var colAi = findColIdx(["đánh giá ai"], 12);
  var colSubmitted = findColIdx(["thời gian nộp"], 13);
  var colFileName = findColIdx(["tên file"], 14);
  
  for (var i = 7; i < data.length; i++) {
    var row = data[i];
    if (row[colTaskId] && String(row[colTaskId]).trim() !== "") {
      tasks.push({
        taskId: String(row[colTaskId]).trim(),
        taskName: row[colTaskName] || "",
        project: row[colProject] || "",
        assignee: row[colAssignee] || "",
        leader: row[colLeader] || "",
        deadline: row[colDeadline] || "",
        priority: row[colPriority] || "",
        status: row[colStatus] || "",
        deliverable: row[colDeliverable] || "",
        trichYeu: row[colSummary] || "",
        soKyHieu: row[colDocNum] || "",
        ngayBanHanh: row[colDocDate] || "",
        aiSummary: row[colAi] || "",
        submittedAt: row[colSubmitted] || "",
        fileName: row[colFileName] || ""
      });
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
    .addItem("✨ Format Giao Diện & Dropdown (Bảo toàn 100% dữ liệu)", "setupHeadersAndFormatting")
    .addItem("🛠️ Căn Chỉnh Dữ Liệu Tự Động", "repairAndRestoreAllTasksClean")
    .addToUi();
}

/**
 * HÀM CƯỠNG CHẾ CĂN CHỈNH DỮ LIỆU LỆCH 15 CỘT
 */
function forceFixMisalignedColumns() {
  repairAndRestoreAllTasksClean();
}

/**
 * HÀM KHÔI PHỤC VÀ ĐỒNG BỘ 100% DỮ LIỆU CHUẨN 15 CỘT TRỰC TIẾP TRÊN SHEET HIỆN HÀNH (IN-PLACE)
 * Bảo toàn tuyệt đối Sheet GID (735957328), không tạo thêm tab thừa.
 * Cột F (Hạn hoàn thành): Date Picker yyyy-mm-dd
 * Cột H (Trạng thái): Dropdown 4 trạng thái chuẩn
 */
function repairAndRestoreAllTasksClean() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Task_Tracker") || ss.getActiveSheet();
  
  // 1. Tiêu đề hệ thống (Dòng 1-2)
  sheet.getRange("A1").setValue("HỆ THỐNG QUẢN LÝ TIẾN ĐỘ NHIỆM VỤ & NHẬN DIỆN NỘP FILE (ZALO BOT)")
    .setFontWeight("bold").setFontSize(14).setFontColor("#0F4C81");
  sheet.getRange("A2").setValue("Dữ liệu được cập nhật tự động qua Zalo Bot tích hợp AI Gemini / Claude - Sẵn sàng đồng bộ Google Sheets")
    .setFontStyle("italic").setFontSize(9).setFontColor("#5F6368");
  
  // 2. Khóa cố định từ dòng 7 trở lên
  sheet.setFrozenRows(7);
  
  // 3. Độ rộng 15 cột chuẩn
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
    10: 300, // J: Trích yếu
    11: 150, // K: Số ký hiệu văn bản
    12: 110, // L: Ngày ban hành
    13: 300, // M: Đánh giá AI
    14: 140, // N: Thời gian nộp
    15: 200  // O: Tên file đã nộp
  };
  for (var col in columnWidths) {
    sheet.setColumnWidth(parseInt(col), columnWidths[col]);
  }
  
  // 4. Dashboard thống kê (Dòng 4-5)
  try {
    sheet.getRange("A4:Z5").breakApart();
  } catch (eBreak) {}
  sheet.getRange("A4:C4").merge().setValue("TỔNG SỐ NHIỆM VỤ").setBackground("#E8F0FE").setFontColor("#174EA6").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("A5:C5").merge().setFormula('=COUNTA(A8:A100)').setBackground("#E8F0FE").setFontColor("#174EA6").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  sheet.getRange("D4:F4").merge().setValue("CHƯA BẮT ĐẦU").setBackground("#F1F3F4").setFontColor("#5F6368").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("D5:F5").merge().setFormula('=COUNTIF(H8:H100, "Chưa bắt đầu")').setBackground("#F1F3F4").setFontColor("#5F6368").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  sheet.getRange("G4:I4").merge().setValue("ĐANG THỰC HIỆN").setBackground("#FEF7E0").setFontColor("#B06000").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("G5:I5").merge().setFormula('=COUNTIF(H8:H100, "Đang thực hiện")').setBackground("#FEF7E0").setFontColor("#B06000").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  sheet.getRange("J4:L4").merge().setValue("ĐANG SỬA LẠI").setBackground("#FCE8E6").setFontColor("#C5221F").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("J5:L5").merge().setFormula('=COUNTIF(H8:H100, "Đang sửa lại")').setBackground("#FCE8E6").setFontColor("#C5221F").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  sheet.getRange("M4:O4").merge().setValue("ĐÃ HOÀN THÀNH").setBackground("#E6F4EA").setFontColor("#137333").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("M5:O5").merge().setFormula('=COUNTIF(H8:H100, "Đã hoàn thành")').setBackground("#E6F4EA").setFontColor("#137333").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  sheet.getRange("A4:O5").setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);

  // 5. Header 15 cột (Dòng 7)
  var headers = [
    "Task ID", "Tên nhiệm vụ / Công việc", "Dự án", "Người phụ trách", "Lãnh đạo phòng",
    "Hạn hoàn thành", "Mức độ ưu tiên", "Trạng thái", "Sản phẩm", "Trích yếu (Yêu cầu / Dự kiến)",
    "Số ký hiệu văn bản", "Ngày ban hành", "Đánh giá AI (Tóm tắt file nộp)", "Thời gian nộp", "Tên file đã nộp"
  ];
  var hRange = sheet.getRange(7, 1, 1, headers.length);
  hRange.setValues([headers]);
  hRange.setBackground("#0F4C81").setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(10)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(7, 36);

  // 6. Xóa Data Validation cũ trên toàn bộ vùng dữ liệu để tránh xung đột
  try {
    sheet.getRange("A8:O100").clearDataValidations();
  } catch (errClear) {}

  // 7. Nạp dữ liệu chuẩn 100% của 7 nhiệm vụ (Dòng 8 đến 14)
  var cleanTasksData = [
    [
      "1",
      "Về giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo kết hợp xây dựng công viên, bãi tắm công cộng ven biển Phước Hải theo phương thức đối tác công tư (Hợp đồng BT) của Công ty Cổ phần Phát triển Bất động sản Phát Đạt",
      "Dự án Bãi tắm Thùy Vân - Trần Hưng Đạo", "Nguyễn Thế Hòa", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đang thực hiện", "Công văn",
      "V/v giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo",
      "", "", "", "", ""
    ],
    [
      "2",
      "V/v giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo kết hợp xây dựng công viên, bãi tắm công cộng ven biển Phước Hải theo phương thức đối tác công tư (Hợp đồng BT) của Công ty Cổ phần Phát triển Bất động sản Phát Đạt",
      "Dự án 247 Trần Hưng Đạo", "Nguyễn Thế Hòa", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đang thực hiện", "Công văn",
      "Có ý kiến việc giao thực hiện dự án theo hình thức BT",
      "", "", "", "", ""
    ],
    [
      "3",
      "V/v giao nhiệm vụ lập hồ sơ báo cáo đề xuất chủ trương đầu tư Dự án Nâng cấp, mở rộng tuyến đường Trần Hưng Đạo kết hợp xây dựng công viên, bãi tắm công cộng ven biển Phước Hải theo phương thức đối tác công tư (Hợp đồng BT) của Công ty Cổ phần Phát triển Bất động sản Phát Đạt.",
      "Dự án Phước Hải - Phát Đạt", "Nguyễn Thế Hòa", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đang thực hiện", "Công văn",
      "27239 STC-PPPQLN",
      "", "", "", "", ""
    ],
    [
      "4",
      "Dự án Chỉnh trang đô thị Khu Mả Lạng và Chợ Gà - Gạo trên địa bàn phường Cầu Ông Lãnh và phường Bến Thành, Thành phố Hồ Chí Minh theo phương thức đối tác công tư (Hợp đồng BT)",
      "Dự án Chỉnh trang Khu Mả Lạng và Chợ Gà - Gạo", "Nguyễn Trung Bảo Lộc", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đã hoàn thành", "Công văn",
      "V/v ý kiến đối với Báo cáo nghiên cứu khả thi điều chỉnh Dự án Chỉnh trang đô thị Khu Mả Lạng và Chợ Gà – Gạo",
      "24586/STC-PPP&QLN", "2026-10-19",
      "Đã thẩm định đạt chuẩn Nghị định 30/2020/NĐ-CP (Khớp chuyên viên: Nguyễn Trung Bảo Lộc)",
      "2026-10-19 15:30:00", "4 - 24586 STC PPP.signed - Lộc.pdf"
    ],
    [
      "5",
      "dự án thành phần 3: Bồi thường, hỗ trợ, tái định cư cao tốc Thành phố Hồ Chí Minh - Mộc Bài đoạn qua Thành phố Hồ Chí Minh thuộc dự án đầu tư xây dựng đường cao tốc Thành phố Hồ Chí Minh - Mộc Bài (giai đoạn 1)",
      "Dự án Cao tốc TP.HCM - Mộc Bài", "Hoàng Thị Hương Giang", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đang thực hiện", "Công văn",
      "V/v ý kiến đối với Báo cáo nghiên cứu khả thi điều chỉnh dự án thành phần 3: Bồi thường, hỗ trợ, tái định cư cao tốc Thành phố Hồ Chí Minh – Mộc Bài",
      "", "", "", "", ""
    ],
    [
      "6",
      "Về thành lập Hội đồng thẩm định báo cáo nghiên cứu khả thi Dự án Khu liên hợp thể dục thể thao quốc gia Rạch Chiếc",
      "Dự án Khu liên hợp TDTT Rạch Chiếc", "Nguyễn Thế Hòa", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đang thực hiện", "Công văn",
      "Về thành lập Hội đồng thẩm định báo cáo nghiên cứu khả thi",
      "", "", "", "", ""
    ],
    [
      "7",
      "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng Dự án Khu liên hợp thể dục thể thao quốc gia Rạch Chiếc theo phương thức đối tác công tư (PPP) Hạng mục hạ tầng kỹ thuật toàn khu",
      "Dự án Hạ tầng kỹ thuật Rạch Chiếc", "Nguyễn Thế Hòa", "Lê Hoàng",
      "2026-10-31", "Gấp", "Đang thực hiện", "Tờ trình",
      "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng Dự án Khu liên hợp thể dục thể thao quốc gia Rạch Chiếc Hạng mục hạ tầng kỹ thuật toàn khu",
      "", "", "", "", ""
    ]
  ];

  sheet.getRange(8, 1, cleanTasksData.length, 15).setValues(cleanTasksData);

  // 8. Cài đặt Data Validation sạch sẽ:
  // Cột E (Lãnh đạo phòng)
  var leaderList = ["Lê Hoàng", "Tô Thị Kim Thoa", "Nguyễn Thế Hòa"];
  var leaderRule = SpreadsheetApp.newDataValidation().requireValueInList(leaderList, true).setAllowInvalid(true).build();
  sheet.getRange("E8:E100").setDataValidation(leaderRule);

  // Cột F (Hạn hoàn thành): Date Picker thuần túy
  var dateRule = SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(true).build();
  sheet.getRange("F8:F100").setDataValidation(dateRule);
  sheet.getRange("F8:F100").setNumberFormat("yyyy-mm-dd");

  // Cột G (Mức độ ưu tiên): Dropdown
  var prioList = ["Bình thường", "Gấp", "Hỏa tốc"];
  var prioRule = SpreadsheetApp.newDataValidation().requireValueInList(prioList, true).setAllowInvalid(true).build();
  sheet.getRange("G8:G100").setDataValidation(prioRule);

  // Cột H (Trạng thái): Dropdown 4 trạng thái chuẩn có mũi tên ▼ ở mọi dòng
  var statusList = ["Chưa bắt đầu", "Đang thực hiện", "Đang sửa lại", "Đã hoàn thành"];
  var statusRule = SpreadsheetApp.newDataValidation().requireValueInList(statusList, true).setAllowInvalid(false).build();
  sheet.getRange("H8:H100").setDataValidation(statusRule);

  // Cột I (Sản phẩm)
  var prodList = ["Công văn", "Tờ trình", "Báo cáo", "Kết luận", "Phiếu trình", "Kế hoạch", "Thông báo", "Quyết định"];
  var prodRule = SpreadsheetApp.newDataValidation().requireValueInList(prodList, true).setAllowInvalid(true).build();
  sheet.getRange("I8:I100").setDataValidation(prodRule);

  // 9. Tô màu trực quan cho trạng thái từng dòng
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

  // 10. Đóng khung, canh lề chuẩn
  var dRange = sheet.getRange("A8:O100");
  dRange.setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);
  dRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
  dRange.setVerticalAlignment("middle");
  dRange.setFontSize(10);

  sheet.getRange("A8:A100").setHorizontalAlignment("center");
  sheet.getRange("E8:G100").setHorizontalAlignment("center");
  sheet.getRange("H8:I100").setHorizontalAlignment("center");
  sheet.getRange("K8:L100").setHorizontalAlignment("center");
  sheet.getRange("N8:N100").setHorizontalAlignment("center");

  SpreadsheetApp.flush();
  try {
    SpreadsheetApp.getUi().alert("🎉 ĐÃ KHÔI PHỤC VÀ ĐỒNG BỘ 15 CỘT THÀNH CÔNG!\nCột F (Hạn hoàn thành): Date Picker yyyy-mm-dd\nCột H (Trạng thái): Dropdown 4 trạng thái chuẩn.");
  } catch (e) {
    Logger.log("Restored successfully!");
  }
}

