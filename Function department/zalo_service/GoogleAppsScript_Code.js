/**
 * GOOGLE APPS SCRIPT CHO HỆ THỐNG ZALO BOT & AI REVIEW NHIỆM VỤ (13 CỘT)
 * SỞ TÀI CHÍNH TP.HCM - PHÒNG HỢP TÁC CÔNG TƯ & QUẢN LÝ NỢ (PPP)
 */

function setupHeadersAndFormatting() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.setFrozenRows(7); // Khóa cố định từ dòng 7 trở lên
  
  // 1. Cấu hình độ rộng từng cột chuẩn thẩm mỹ công sở
  var columnWidths = {
    1: 75,   // A: Task ID
    2: 260,  // B: Tên nhiệm vụ / Công việc
    3: 150,  // C: Người phụ trách
    4: 120,  // D: Hạn hoàn thành
    5: 110,  // E: Mức độ ưu tiên
    6: 140,  // F: Trạng thái
    7: 170,  // G: Sản phẩm yêu cầu
    8: 300,  // H: Trích yếu (Yêu cầu / Dự kiến)
    9: 160,  // I: Số ký hiệu văn bản
    10: 120, // J: Ngày ban hành
    11: 300, // K: Đánh giá AI (Tóm tắt file nộp)
    12: 150, // L: Thời gian nộp
    13: 220  // M: Tên file đã nộp
  };
  
  for (var col in columnWidths) {
    sheet.setColumnWidth(parseInt(col), columnWidths[col]);
  }
  
  // 2. Định dạng Dashboard thống kê (Dòng 4-5) trải đều toàn bộ cột A -> M
  // A4:C5 - Tổng số nhiệm vụ
  sheet.getRange("A4:C4").merge().setValue("TỔNG SỐ NHIỆM VỤ").setBackground("#E8F0FE").setFontColor("#174EA6").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("A5:C5").merge().setFormula('=COUNTA(A8:A100)').setBackground("#E8F0FE").setFontColor("#174EA6").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // D4:E5 - Chưa bắt đầu
  sheet.getRange("D4:E4").merge().setValue("CHƯA BẮT ĐẦU").setBackground("#F1F3F4").setFontColor("#5F6368").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("D5:E5").merge().setFormula('=COUNTIF(F8:F100, "Chưa bắt đầu")').setBackground("#F1F3F4").setFontColor("#5F6368").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // F4:G5 - Đang thực hiện
  sheet.getRange("F4:G4").merge().setValue("ĐANG THỰC HIỆN").setBackground("#FEF7E0").setFontColor("#B06000").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("F5:G5").merge().setFormula('=COUNTIF(F8:F100, "Đang thực hiện")').setBackground("#FEF7E0").setFontColor("#B06000").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // H4:I5 - Đang sửa lại (Cảnh báo)
  sheet.getRange("H4:I4").merge().setValue("ĐANG SỬA LẠI").setBackground("#FCE8E6").setFontColor("#C5221F").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("H5:I5").merge().setFormula('=COUNTIF(F8:F100, "Đang sửa lại")').setBackground("#FCE8E6").setFontColor("#C5221F").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // J4:M5 - Đã hoàn thành
  sheet.getRange("J4:M4").merge().setValue("ĐÃ HOÀN THÀNH").setBackground("#E6F4EA").setFontColor("#137333").setFontWeight("bold").setHorizontalAlignment("center");
  sheet.getRange("J5:M5").merge().setFormula('=COUNTIF(F8:F100, "Đã hoàn thành")').setBackground("#E6F4EA").setFontColor("#137333").setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");

  // Đóng khung viền mỏng cho Dashboard
  sheet.getRange("A4:M5").setBorder(true, true, true, true, true, true, "#DADCE0", SpreadsheetApp.BorderStyle.SOLID);

  // 3. 13 Cột Tiêu đề Header (Dòng 7)
  var headers = [
    "Task ID",
    "Tên nhiệm vụ / Công việc",
    "Người phụ trách",
    "Hạn hoàn thành",
    "Mức độ ưu tiên",
    "Trạng thái",
    "Sản phẩm yêu cầu",
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

  // 4. Cập nhật 4 nhiệm vụ thực tế của Phòng PPP & QLN
  var realTasks = [
    [
      "1",
      "Đề xuất nghiên cứu đầu tư 03 cảng thủy nội địa Bạch Đằng (PPP)",
      "Phan Công Hận",
      "2026-09-25",
      "Gấp",
      "Đang thực hiện",
      "Báo cáo / Công văn (.doc / .pdf)",
      "V/v đề xuất nghiên cứu đầu tư dự án Xây dựng 03 cảng thủy nội địa hành khách khu công viên Bạch Đằng (từ Hàm Nghi đến Ba Son) theo hình thức đối tác công tư (PPP)",
      "", "", "", "", ""
    ],
    [
      "2",
      "Đăng ký lịch làm việc với Thanh tra Chính phủ về các dự án BT Thủ Thiêm",
      "Phan Công Hận",
      "2026-09-26",
      "Gấp",
      "Đang thực hiện",
      "Báo cáo / Dự thảo văn bản (.pdf)",
      "Đăng ký làm việc với Thanh tra Chính phủ về phương án thanh toán các dự án BT trong khu đô thị mới Thủ Thiêm theo Nghị định số 91/2025/NĐ-CP",
      "", "", "", "", ""
    ],
    [
      "3",
      "Báo cáo rà soát giải ngân vốn ODA và quản lý nợ công quý III/2026",
      "Nguyễn Thế Hòa",
      "2026-09-24",
      "Gấp",
      "Đang thực hiện",
      "Báo cáo (.docx / .pdf)",
      "Báo cáo tình hình giải ngân nguồn vốn ODA và các khoản vay lại của chính quyền địa phương",
      "", "", "", "", ""
    ],
    [
      "4",
      "Thẩm định phương án tài chính dự án PPP Cầu Cần Giờ",
      "Nguyễn Thế Hòa",
      "2026-09-28",
      "Bình thường",
      "Đang thực hiện",
      "Tờ trình (.docx)",
      "Tờ trình thẩm định báo cáo nghiên cứu khả thi dự án Đầu tư xây dựng Cầu Cần Giờ theo phương thức PPP",
      "", "", "", "", ""
    ]
  ];

  for (var i = 0; i < realTasks.length; i++) {
    var rowIdx = 8 + i;
    sheet.getRange(rowIdx, 1, 1, 13).setValues([realTasks[i]]);
    // Đặt màu trạng thái Đang thực hiện
    sheet.getRange(rowIdx, 6).setBackground("#FEF7E0").setFontColor("#B06000");
  }

  // 5. Căn lề và viền dữ liệu dòng 8-25
  var dataRange = sheet.getRange("A8:M25");
  dataRange.setVerticalAlignment("middle");
  dataRange.setFontSize(10);
  dataRange.setBorder(true, true, true, true, true, true, "#E0E0E0", SpreadsheetApp.BorderStyle.SOLID);
  
  // Căn giữa các cột mã số, ngày, trạng thái
  sheet.getRange("A8:A25").setHorizontalAlignment("center");
  sheet.getRange("D8:F25").setHorizontalAlignment("center");
  sheet.getRange("I8:J25").setHorizontalAlignment("center");
  sheet.getRange("L8:L25").setHorizontalAlignment("center");
  
  SpreadsheetApp.flush();
  Logger.log("Đã làm đẹp và cập nhật 4 nhiệm vụ thực tế thành công!");
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var postData = JSON.parse(e.postData.contents);
    
    var taskId = String(postData.taskId).trim();
    var status = postData.status || "Đã hoàn thành";
    var summary = postData.summary || "";
    var fileName = postData.fileName || "";
    var docNumber = postData.docNumber || "";
    var docDate = postData.docDate || "";
    var actualSummary = postData.actualSummary || "";
    
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
    
    var statusCell = sheet.getRange(targetRow, 6);
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
    
    // Cập nhật trích yếu thực tế nếu có
    if (actualSummary) sheet.getRange(targetRow, 8).setValue(actualSummary);
    if (docNumber) sheet.getRange(targetRow, 9).setValue(docNumber);
    if (docDate) sheet.getRange(targetRow, 10).setValue(docDate);
    sheet.getRange(targetRow, 11).setValue(summary);
    sheet.getRange(targetRow, 12).setValue(formattedTime);
    sheet.getRange(targetRow, 13).setValue(fileName);
    
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
  
  for (var i = 7; i < data.length; i++) {
    var row = data[i];
    if (row[0] && String(row[0]).trim() !== "") {
      tasks.push({
        taskId: row[0],
        taskName: row[1],
        assignee: row[2],
        deadline: row[3],
        priority: row[4],
        status: row[5],
        deliverable: row[6],
        trichYeu: row[7] || "",
        soKyHieu: row[8] || "",
        ngayBanHanh: row[9] || "",
        aiSummary: row[10] || "",
        submittedAt: row[11] || "",
        fileName: row[12] || ""
      });
    }
  }
  
  return ContentService.createTextOutput(JSON.stringify({
    success: true,
    data: tasks
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * TỰ ĐỘNG PHÁT BẢN TIN NHẮC VIỆC LÊN ZALO GROUP HÀNG NGÀY (08:00 SÁNG & 17:30 CHIỀU)
 * Chạy 100% trên Đám mây Google Apps Script - Không cần bật máy tính.
 */
function sendDailyZaloReminder() {
  var botToken = "1175912593990733827:IQHQDAkiFOfwODzTmEKdPvfCSbDJubszVeLXcvxwqTSZXPbNaBaTLYQAmeXpAWMX";
  var targetGroupId = "2327925421752384731";
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues();
  
  var now = new Date();
  var formattedDate = Utilities.formatDate(now, "GMT+7", "dd/MM/yyyy HH:mm");
  
  var messageLines = [
    "📢 ═════ [NHẮC VIỆC TỰ ĐỘNG - GOOGLE WORKSPACE CLOUD] ═════",
    "⏰ Thời gian phát tin: " + formattedDate,
    "📋 Danh sách nhiệm vụ đang xử lý tại Phòng PPP & QLN:\n"
  ];
  
  var pendingCount = 0;
  for (var i = 7; i < data.length; i++) {
    var row = data[i];
    if (row[0] && String(row[0]).trim() !== "" && row[5] !== "Đã hoàn thành") {
      pendingCount++;
      messageLines.push("👤 **" + row[2] + "**:");
      messageLines.push("   • 📌 Task [" + row[0] + "]: " + row[1]);
      messageLines.push("     ⏳ Hạn hoàn thành: " + row[3] + " | Trạng thái: " + row[5] + "\n");
    }
  }
  
  if (pendingCount === 0) {
    messageLines.push("🎉 Tất cả các nhiệm vụ của Phòng đã được hoàn thành xuất sắc!");
  } else {
    messageLines.push("📊 Tổng số nhiệm vụ chưa hoàn thành: " + pendingCount);
    messageLines.push("💡 Ghi chú: Chuyên viên vui lòng nộp file đính kèm trực tiếp vào Zalo để tự động nghiệm thu.");
  }
  
  var payload = {
    "chat_id": targetGroupId,
    "text": messageLines.join("\n"),
    "parse_mode": "markdown"
  };
  
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };
  
  UrlFetchApp.fetch("https://bot-api.zaloplatforms.com/bot" + botToken + "/sendMessage", options);
}

function createDailyTriggers() {
  // Xóa các trigger cũ để tránh trùng lặp
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  
  // 1. Kích hoạt Trigger 08:00 Sáng
  ScriptApp.newTrigger("sendDailyZaloReminder")
    .timeBased()
    .atHour(8)
    .nearMinute(0)
    .everyDays(1)
    .inTimezone("Asia/Ho_Chi_Minh")
    .create();

  // 2. Kích hoạt Trigger 17:30 Chiều
  ScriptApp.newTrigger("sendDailyZaloReminder")
    .timeBased()
    .atHour(17)
    .nearMinute(30)
    .everyDays(1)
    .inTimezone("Asia/Ho_Chi_Minh")
    .create();
    
  Logger.log("✅ Đã kích hoạt Trigger tự động phát bản tin 08:00 & 17:30 hàng ngày thành công!");
}
