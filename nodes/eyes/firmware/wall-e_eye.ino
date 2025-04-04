#include <vector>
#include <string>
#include <TFT_eSPI.h>
#include <SPI.h>
#include <SD.h>
#include <math.h>
#include <algorithm>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <JPEGDecoder.h> // Using JPEG format for static images

WebServer server(80);
Preferences prefs;


#ifdef ARDUINO_ARCH_RP2350
#undef PICO_BUILD
#endif
#include "AnimatedGIF.h"

AnimatedGIF gif;
TFT_eSPI tft = TFT_eSPI();

// rule: loop GIF at least during 3s, maximum 5 times, and don't loop/animate longer than 30s per GIF
const int maxLoopIterations =     1; // stop after this amount of loops
const int maxLoopsDuration  =  3000; // ms, max cumulated time after the GIF will break loop
const int maxGifDuration    =240000; // ms, max GIF duration

// used to center image based on GIF dimensions
static int xOffset = 0;
static int yOffset = 0;

static int totalFiles = 0; // GIF files count
static int currentFile = 0;
static int lastFile = -1;

char GifComment[256];

static File FSGifFile; // temp gif file holder
static File GifRootFolder; // directory listing
std::vector<std::string> GifFiles; // GIF files path
static File uploadFile; // file upload handler
bool uploadTooLarge = false; // flag for oversized uploads
volatile bool cancelPlayback = false; // flag to cancel ongoing GIF playback
#define DISPLAY_WIDTH 240

static void MyCustomDelay( unsigned long ms ) {
  delay( ms );
  // log_d("delay %d\n", ms);
}

static void * GIFOpenFile(const char *fname, int32_t *pSize)
{
  // log_d("GIFOpenFile( %s )\n", fname );
  FSGifFile = SD.open(fname);
  if (FSGifFile) {
    *pSize = FSGifFile.size();
    return (void *)&FSGifFile;
  }
  return NULL;
}

static void GIFCloseFile(void *pHandle)
{
  File *f = static_cast<File *>(pHandle);
  if (f != NULL)
     f->close();
}

static int32_t GIFReadFile(GIFFILE *pFile, uint8_t *pBuf, int32_t iLen)
{
  int32_t iBytesRead;
  iBytesRead = iLen;
  File *f = static_cast<File *>(pFile->fHandle);
  // Note: If you read a file all the way to the last byte, seek() stops working
  if ((pFile->iSize - pFile->iPos) < iLen)
      iBytesRead = pFile->iSize - pFile->iPos - 1; // <-- ugly work-around
  if (iBytesRead <= 0)
      return 0;
  iBytesRead = (int32_t)f->read(pBuf, iBytesRead);
  pFile->iPos = f->position();
  return iBytesRead;
}

static int32_t GIFSeekFile(GIFFILE *pFile, int32_t iPosition)
{
  int i = micros();
  File *f = static_cast<File *>(pFile->fHandle);
  f->seek(iPosition);
  pFile->iPos = (int32_t)f->position();
  i = micros() - i;
  // log_d("Seek time = %d us\n", i);
  return pFile->iPos;
}

static void TFTDraw(int x, int y, int w, int h, uint16_t* lBuf )
{
  tft.pushRect( x+xOffset, y+yOffset, w, h, lBuf );
}

// Draw a line of image directly on the LCD
void GIFDraw(GIFDRAW *pDraw)
{
  uint8_t *s;
  uint16_t *d, *usPalette, usTemp[320];
  int x, y, iWidth;

  iWidth = pDraw->iWidth;
  if (iWidth > DISPLAY_WIDTH)
      iWidth = DISPLAY_WIDTH;
  usPalette = pDraw->pPalette;
  y = pDraw->iY + pDraw->y; // current line

  s = pDraw->pPixels;
  if (pDraw->ucDisposalMethod == 2) {// restore to background color
    for (x=0; x<iWidth; x++) {
      if (s[x] == pDraw->ucTransparent)
          s[x] = pDraw->ucBackground;
    }
    pDraw->ucHasTransparency = 0;
  }
  // Apply the new pixels to the main image
  if (pDraw->ucHasTransparency) { // if transparency used
    uint8_t *pEnd, c, ucTransparent = pDraw->ucTransparent;
    int x, iCount;
    pEnd = s + iWidth;
    x = 0;
    iCount = 0; // count non-transparent pixels
    while(x < iWidth) {
      c = ucTransparent-1;
      d = usTemp;
      while (c != ucTransparent && s < pEnd) {
        c = *s++;
        if (c == ucTransparent) { // done, stop
          s--; // back up to treat it like transparent
        } else { // opaque
            *d++ = usPalette[c];
            iCount++;
        }
      } // while looking for opaque pixels
      if (iCount) { // any opaque pixels?
        TFTDraw( pDraw->iX+x, y, iCount, 1, (uint16_t*)usTemp );
        x += iCount;
        iCount = 0;
      }
      // no, look for a run of transparent pixels
      c = ucTransparent;
      while (c == ucTransparent && s < pEnd) {
        c = *s++;
        if (c == ucTransparent)
            iCount++;
        else
            s--;
      }
      if (iCount) {
        x += iCount; // skip these
        iCount = 0;
      }
    }
  } else {
    s = pDraw->pPixels;
    // Translate the 8-bit pixels through the RGB565 palette (already byte reversed)
    for (x=0; x<iWidth; x++)
      usTemp[x] = usPalette[*s++];
    TFTDraw( pDraw->iX, y, iWidth, 1, (uint16_t*)usTemp );
  }
} /* GIFDraw() */

int gifPlay( char* gifPath )
{ // 0=infinite
  gif.begin(BIG_ENDIAN_PIXELS);
  if( ! gif.open( gifPath, GIFOpenFile, GIFCloseFile, GIFReadFile, GIFSeekFile, GIFDraw ) ) {
    // log_n("Could not open gif %s", gifPath );
    return maxLoopsDuration;
  }

  cancelPlayback = false; // Reset cancel flag before starting
  const float speedFactor = 0.5; // adjust this value to fine-tune playback speed
  int frameDelay = 0; // store delay for the last frame
  int then = 0; // store overall delay
  bool showcomment = false;

  // center the GIF !!
  int w = gif.getCanvasWidth();
  int h = gif.getCanvasHeight();
  xOffset = ( tft.width()  - w )  /2;
  yOffset = ( tft.height() - h ) /2;

  if( lastFile != currentFile ) {
    // log_n("Playing %s [%d,%d] with offset [%d,%d]", gifPath, w, h, xOffset, yOffset );
    lastFile = currentFile;
    showcomment = true;
  }

  while (gif.playFrame(true, &frameDelay)) {
    if (cancelPlayback) {
      // Cancel the playback if a new command has arrived
      break;
    }
    if (showcomment) {
      if (gif.getComment(GifComment)) {
        // log_n("GIF Comment: %s", GifComment);
      }
    }
    unsigned long adjustedDelay = (unsigned long)(frameDelay * speedFactor);
    then += adjustedDelay;
    if (then > maxGifDuration) { // avoid being trapped in infinite GIF's
      // log_w("Broke the GIF loop, max duration exceeded");
      break;
    }
    unsigned long frameStart = millis();
    while (millis() - frameStart < adjustedDelay) {
      server.handleClient();
      delay(1);
    }
  }

  gif.close();
  return then;
}

// Function to draw a line of JPEG pixels to the TFT display
void jpegRender(int xpos, int ypos) {
  // Retrieve information about the image
  uint16_t *pImg;
  uint16_t mcu_w = JpegDec.MCUWidth;
  uint16_t mcu_h = JpegDec.MCUHeight;
  uint32_t max_x = JpegDec.width;
  uint32_t max_y = JpegDec.height;

  // Calculate center position
  int centerX = (tft.width() - max_x) / 2;
  int centerY = (tft.height() - max_y) / 2;
  
  // Adjust for centering
  xpos += centerX;
  ypos += centerY;

  // Retrieve the pixel data
  pImg = JpegDec.pImage;

  // Check if the MCU is out of bounds
  if ((xpos >= tft.width()) || (ypos >= tft.height())) return;
  
  // Push the pixels to the TFT display
  tft.pushImage(xpos, ypos, mcu_w, mcu_h, pImg);
}

// Function to display a JPEG file
bool displayJPEG(const char *filename) {
  cancelPlayback = true;
  
  // Clear the screen before drawing
  tft.fillScreen(TFT_BLACK);
  
  File jpegFile = SD.open(filename, FILE_READ);
  if (!jpegFile) {
    Serial.println("JPEG file not found");
    
    // Show error placeholder
    int centerX = tft.width() / 2;
    int centerY = tft.height() / 2;
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);
    tft.drawString("Error: Image not found", centerX, centerY - 30);
    tft.drawString(filename, centerX, centerY);
    
    return false;
  }
  
  // Start JPEG decoding
  bool decoded = JpegDec.decodeSdFile(jpegFile);
  if (decoded) {
    Serial.println("JPEG image decoded successfully");
    
    // Retrieve information about the image
    uint32_t max_x = JpegDec.width;
    uint32_t max_y = JpegDec.height;
    Serial.printf("JPEG image specs: (%d x %d)\n", max_x, max_y);
    
    // Start rendering blocks (Minimum Coded Units)
    uint32_t mcu_count = 0;
    while (JpegDec.read()) {
      mcu_count++;
      
      // Get MCU coordinates
      int x = JpegDec.MCUx;
      int y = JpegDec.MCUy;
      
      // Render the current MCU block
      jpegRender(x, y);
      
      // Handle other tasks during rendering
      if (mcu_count % 20 == 0) {
        server.handleClient();
        yield();
      }
    }
    
    jpegFile.close();
    return true;
  } else {
    Serial.println("JPEG decode error");
    jpegFile.close();
    
    // Show error placeholder
    int centerX = tft.width() / 2;
    int centerY = tft.height() / 2;
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);
    tft.drawString("Error decoding JPEG", centerX, centerY - 30);
    tft.drawString(filename, centerX, centerY);
    
    return false;
  }
}

// Function to determine image type and display accordingly
bool displayImage(const char *filename) {
  String fname = String(filename);
  fname.toLowerCase();
  
  if (fname.endsWith(".jpg") || fname.endsWith(".jpeg")) {
    return displayJPEG(filename);
  } else if (fname.endsWith(".gif")) {
    int playTime = gifPlay((char*)filename);
    return true;
  } else {
    // For unsupported formats
    tft.fillScreen(TFT_BLACK);
    int centerX = tft.width() / 2;
    int centerY = tft.height() / 2;
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);
    tft.drawString("Unsupported format", centerX, centerY - 30);
    tft.drawString(filename, centerX, centerY);
    return false;
  }
}

int getGifInventory( const char* basePath )
{
  int amount = 0;
  GifRootFolder = SD.open(basePath);
  if(!GifRootFolder){
    // log_n("Failed to open directory");
    return 0;
  }

  if(!GifRootFolder.isDirectory()){
    // log_n("Not a directory");
    return 0;
  }

  File file = GifRootFolder.openNextFile();

  tft.setTextColor( TFT_WHITE, TFT_BLACK );
  tft.setTextSize( 2 );

  int textPosX = tft.width()/2 - 16;
  int textPosY = tft.height()/2 - 10;

  tft.drawString("GIF Files:", textPosX-40, textPosY-20 );

  while( file ) {
    if(!file.isDirectory()) {
      String fname = file.name();
      if (fname.charAt(0) != '.') {
        GifFiles.push_back(std::string(fname.c_str()));
        amount++;
        tft.drawString(String(amount), textPosX, textPosY );
      }
      file.close();
    }
    file = GifRootFolder.openNextFile();
  }
  GifRootFolder.close();
  // log_n("Found %d GIF files", amount);
  return amount;
}

String getGifInventoryApi(const char* basePath) {
  String json = "[";
  File root = SD.open(basePath);
  if(!root || !root.isDirectory()){
    return json + "]";
  }
  File file = root.openNextFile();
  bool first = true;
  while(file) {
    if(!file.isDirectory()){
      String fname = file.name();
      if(fname.charAt(0) != '.'){
        if(!first) {
          json += ",";
        }
        json += "\"" + fname + "\"";
        first = false;
      }
    }
    file = root.openNextFile();
  }
  root.close();
  json += "]";
  return json;
}

void handleFileUpload() {
  HTTPUpload& upload = server.upload();
  const unsigned long MAX_SIZE = 10485760; // 10 MB in bytes

  if(upload.status == UPLOAD_FILE_START) {
    if(upload.totalSize > MAX_SIZE) {
      uploadTooLarge = true;
      Serial.println("Upload refused: file too large");
      return;
    }
    String fullPath = "/gif/" + String(upload.filename);
    if(SD.exists(fullPath.c_str())) {
      SD.remove(fullPath.c_str());
    }
    uploadFile = SD.open(fullPath.c_str(), FILE_WRITE);
  } else if(upload.status == UPLOAD_FILE_WRITE) {
    if(uploadTooLarge)
      return;
    if(uploadFile)
      uploadFile.write(upload.buf, upload.currentSize);
  } else if(upload.status == UPLOAD_FILE_END) {
    if(uploadTooLarge)
      return;
    if(uploadFile)
      uploadFile.close();
  }
}

void setup() {
  tft.begin();
  prefs.begin("display", false);
  int rotation = prefs.getInt("rotation", 0);  // 0-3 for quarter turns
  tft.setRotation(rotation);
  
  tft.fillScreen(TFT_BLACK);
  tft.setTextSize(2);
  tft.setTextDatum(MC_DATUM); // center text
  // Show initial statuses:
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  // Center all status info vertically
  int centerY = tft.height()/2;
  tft.drawString("SD: waiting", tft.width()/2, centerY - 40);
  tft.drawString("WiFi: waiting", tft.width()/2, centerY - 20);

  Serial.begin(115200);
  
  pinMode(D2, OUTPUT);
  
  // Update SD status to "initializing" (yellow)
  tft.fillScreen(TFT_BLACK); // Clear entire screen
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("SD: initializing", tft.width()/2, centerY - 30);
  
  if (!SD.begin(D2)) {
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("SD: failed", tft.width()/2, centerY - 30);
    Serial.println("SD initialization failed!");
    delay(1000);
    setup();
  } else {
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("SD: initialized", tft.width()/2, centerY - 30);
    Serial.println("SD initialized.");
  }

  Serial.println("DEBUG: SD card initialized successfully.");
  if (!SD.exists("/gif")) {
    Serial.println("DEBUG: Creating /gif directory...");
    SD.mkdir("/gif");
  }
  
  WiFi.mode(WIFI_STA);
  
  const char* ssid = "wall-e.neuhaus.nrw";
  const char* password = "galactic";
  
  // Update WiFi status to "connecting" (yellow)
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("SD: initialized", tft.width()/2, centerY - 30);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("WiFi: connecting", tft.width()/2, centerY - 10);
  
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  unsigned long wifiTimeout = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - wifiTimeout) < 15000) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("SD: initialized", tft.width()/2, centerY - 30);
    tft.drawString("WiFi: connected", tft.width()/2, centerY - 10);
    String ip = WiFi.localIP().toString();
    // Center status info vertically and horizontally
    int centerY = tft.height()/2;  // Vertical center of display
    tft.drawString("IP: " + ip, tft.width()/2, centerY + 10);
    tft.drawString("API: Ready", tft.width()/2, centerY + 30);
    Serial.println(" Connected!");
    Serial.print("IP Address: ");
    Serial.println(ip);
  } else {
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("SD: initialized", tft.width()/2, centerY - 30);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("WiFi: failed", tft.width()/2, centerY - 10);
    Serial.println("WiFi connection failed!");
  }

  delay(2000); // Show status for 2 seconds

  server.on("/", []() {
    int currentRotation = prefs.getInt("rotation", 0);
    String gifListHtml = "<div class='row'>";
    File root = SD.open("/gif");
    if (root && root.isDirectory()) {
      Serial.println("DEBUG: Successfully opened /gif directory for scanning.");
      File file = root.openNextFile();
      while (file) {
        if (!file.isDirectory()) {
          String fname = file.name();
          if (fname.charAt(0) == '.' || fname.indexOf("_preview") != -1) {
            file = root.openNextFile();
            continue;
          }
          if (fname.endsWith(".gif") || fname.endsWith(".GIF") || 
              fname.endsWith(".jpg") || fname.endsWith(".JPG") ||
              fname.endsWith(".jpeg") || fname.endsWith(".JPEG")) {
            gifListHtml += "<div class='col-sm-6 col-md-4 col-lg-3 mb-3'>";
            gifListHtml += "<div class='card'>";
            gifListHtml += "<div class='preview-container' style='background-color: #000; padding: 10px; display: flex; justify-content: center; align-items: center;'>";
            String baseName = fname.substring(0, fname.lastIndexOf('.'));
            if (baseName.endsWith("_o")) {
              baseName = baseName.substring(0, baseName.length() - 2);
            }
            String ext = fname.substring(fname.lastIndexOf('.'));
            String previewName = baseName + "_preview" + ext;
            String srcURL;
            if(SD.exists((String("/gif/") + previewName).c_str())) {
              srcURL = "/gif/" + previewName;
            } else {
              srcURL = "/gif/" + fname;
            }
            gifListHtml += "<img src='" + srcURL + "' class='card-img-top' alt='" + fname + "' style='cursor:pointer; border-radius:120px;' onclick=\"sendCommand('/playgif?name=" + fname + "')\">";
            gifListHtml += "</div><div class='card-body p-2'>";
            gifListHtml += "<p class='card-text text-center' style='font-size:0.8rem;'>" + fname + "</p>";
            gifListHtml += "<button class='btn btn-danger btn-sm' onclick=\"if(confirm('Are you sure you want to delete " + fname + "?')) { sendCommand('/delete?name=" + fname + "'); window.location.reload(); }\">Delete</button>";
            gifListHtml += "</div>";
            gifListHtml += "</div></div>";
          }
        }
        file = root.openNextFile();
      }
      gifListHtml += "</div>";
      root.close();
    } else {
      Serial.println("DEBUG: Failed to open /gif directory.");
    }
    String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>TFT_eSPI Image Player API</title>";
    html += "<link rel='stylesheet' href='https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'>";
    html += "<style>body { background-color: #f8f9fa; } .header { margin: 20px 0; } .card-img-top { background-color: black; width: 240px; height: 240px; object-fit: cover; display: block; margin: 0 auto; }</style>";
    html += "</head><body><div class='container'>";
    if (server.hasArg("upload") && server.arg("upload") == "success") {
      html += "<div class='alert alert-success mt-3' role='alert'>Upload successful</div>";
    }
    html += "<div class='mb-5'><h2>Image Previews</h2>" + gifListHtml + "</div>";
    html += "<div class='mb-5'><h2>Display Rotation</h2>";
    html += "<div class='btn-group' role='group'>";
    for(int i = 0; i < 4; i++) {
      html += "<button class='btn btn-" + String(i == currentRotation ? "primary" : "secondary") + "' onclick='updateRotation(" + String(i) + ")'>" + String(i * 90) + "°</button>";
    }
    html += "</div>";
    html += "</div>";
    
    html += "<div class='mb-5'>";
    html += "<h2>Commands</h2>";
    html += "<div class='btn-group' role='group'>";
    html += "<button class='btn btn-primary' onclick=\"sendCommand('/open')\">Open</button>";
    html += "<button class='btn btn-primary' onclick=\"sendCommand('/close')\">Close</button>";
    html += "<button class='btn btn-primary' onclick=\"sendCommand('/blink')\">Blink</button>";
    html += "<button class='btn btn-primary' onclick=\"sendCommand('/colorful')\">Colorful</button>";
    html += "</div></div>";
    
    html += "<div class='mb-5'><h2>Upload Image</h2>";
    html += "<form method='POST' action='/upload' enctype='multipart/form-data'>";
    html += "<div class='form-group'>";
    html += "<label for='file'>Select GIF or JPG file:</label>";
    html += "<input type='file' name='file' accept='.gif,.jpg,.jpeg,.GIF,.JPG,.JPEG' class='form-control-file' id='file'>";
    html += "</div>";
    html += "<button type='submit' class='btn btn-primary'>Upload</button>";
    html += "</form></div>";
    html += "<script>function sendCommand(cmd){fetch(cmd).then(response=>response.text()).then(text=>console.log(text));}</script>";
    html += "<script>";
    html += "function updateRotation(val){";
    html += "fetch('/rotate?value='+val).then(response=>response.text()).then(text=>console.log(text));";
    html += "}";
    html += "</script>";
    html += "</div></body></html>";
    server.send(200, "text/html", html);
  });
  server.on("/open", []() {
    cancelPlayback = true;
    tft.fillScreen(TFT_BLACK);
    tft.fillCircle(tft.width()/2, tft.height()/2, 50, TFT_WHITE);
    tft.fillCircle(tft.width()/2, tft.height()/2, 30, TFT_BLUE);
    tft.fillCircle(tft.width()/2, tft.height()/2, 10, TFT_BLACK);
    server.send(200, "text/plain", "Executed command: open");
  });
  server.on("/close", []() {
    cancelPlayback = true;
    tft.fillScreen(TFT_BLACK);
    tft.drawLine(tft.width()/2 - 50, tft.height()/2, tft.width()/2 + 50, tft.height()/2, TFT_WHITE);
    tft.drawLine(tft.width()/2 - 50, tft.height()/2 + 1, tft.width()/2 + 50, tft.height()/2 + 1, TFT_WHITE);
    server.send(200, "text/plain", "Executed command: close");
  });
  server.on("/blink", []() {
    cancelPlayback = true;
    tft.fillScreen(TFT_BLACK);
    tft.drawLine(tft.width()/2 - 50, tft.height()/2, tft.width()/2 + 50, tft.height()/2, TFT_WHITE);
    delay(200);
    tft.fillScreen(TFT_BLACK);
    tft.fillCircle(tft.width()/2, tft.height()/2, 50, TFT_WHITE);
    tft.fillCircle(tft.width()/2, tft.height()/2, 30, TFT_BLUE);
    tft.fillCircle(tft.width()/2, tft.height()/2, 10, TFT_BLACK);
    server.send(200, "text/plain", "Executed command: blink");
  });
  server.on("/colorful", []() {
    cancelPlayback = true;
    unsigned long time = millis();
    for (int yPos = 0; yPos < tft.height(); yPos += 10) {
      for (int xPos = 0; xPos < tft.width(); xPos += 10) {
        float wave = sin((xPos + time / 10.0) * 0.05) + cos((yPos + time / 10.0) * 0.05);
        uint16_t color = tft.color565(
          (int)((sin(wave + time / 1000.0) + 1) * 127.5),
          (int)((cos(wave + time / 1000.0) + 1) * 127.5),
          (int)(((sin(wave) + cos(wave)) / 2 + 1) * 127.5)
        );
        tft.fillRect(xPos, yPos + (int)(10 * sin((xPos + time / 100.0) * 0.1)), 10, 10, color);
      }
    }
    server.send(200, "text/plain", "Executed command: colorful");
  });

  server.on("/gifs", []() {
    String json = getGifInventoryApi("/gif");
    server.send(200, "application/json", json);
  });
  server.on("/playgif", []() {
    cancelPlayback = true;
    if (server.hasArg("name")) {
      String imageName = server.arg("name");
      String fullPath = "/gif/" + imageName;
      
      // Use the unified image display function
      if (displayImage(fullPath.c_str())) {
        server.send(200, "text/plain", "Displaying image: " + imageName);
      } else {
        server.send(500, "text/plain", "Error displaying image: " + imageName);
      }
    } else {
      server.send(400, "text/plain", "Missing image name");
    }
  });
  server.on("/upload", HTTP_GET, []() {
    String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Upload Image</title>";
    html += "<link rel=\"stylesheet\" href=\"https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css\">";
    html += "</head><body><div class=\"container mt-4\">";
    html += "<h1>Upload Image</h1>";
    html += "<form method='POST' action='/upload' enctype='multipart/form-data'>";
    html += "<div class='form-group'>";
    html += "<label for='file'>Select GIF or JPG file:</label>";
    html += "<input type='file' name='file' accept='.gif,.jpg,.jpeg,.GIF,.JPG,.JPEG' class='form-control-file' id='file'>";
    html += "</div>";
    html += "<button type='submit' class='btn btn-primary'>Upload</button>";
    html += "</form>";
    html += "</div></body></html>";
    server.send(200, "text/html", html);
  });
  server.on("/upload", HTTP_POST, []() {
    if(uploadTooLarge) {
      server.send(400, "text/plain", "Upload refused: file too large");
      uploadTooLarge = false; // reset for the next upload
      return;
    }
    server.sendHeader("Location", "/?upload=success");
    server.send(302, "text/plain", "");
  }, handleFileUpload);
  server.on("/delete", []() {
    if (server.hasArg("name")) {
      String gifName = server.arg("name");
      String fullPath = "/gif/" + gifName;
      if (SD.exists(fullPath.c_str())) {
        SD.remove(fullPath.c_str());
        server.send(200, "text/plain", "Deleted gif: " + gifName);
      } else {
        server.send(404, "text/plain", "Gif not found: " + gifName);
      }
    } else {
      server.send(400, "text/plain", "Missing gif name");
    }
  });
  server.on("/rotate", []() {
    if (server.hasArg("value")) {
      int rotation = server.arg("value").toInt();
      if (rotation < 0) rotation = 0;
      if (rotation > 3) rotation = 3;
      prefs.putInt("rotation", rotation);
      tft.setRotation(rotation);
      server.send(200, "text/plain", "Rotation updated to " + String(rotation * 90) + "°");
    } else {
      server.send(400, "text/plain", "Missing rotation value");
    }
  });

  server.serveStatic("/gif", SD, "/gif");
  server.begin();
  Serial.println("HTTP server started");
  delay(2000);
}



void loop() {
  server.handleClient();
  delay(1);
}

