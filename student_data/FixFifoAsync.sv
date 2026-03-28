// Asynchronous FIFO with Gray-code pointer synchronization.
//
// 8-entry, 8-bit FIFO. Write and read pointers are 4 bits (3 address + 1 wrap).
// Gray-coded pointers are synchronized across clock domains to safely detect
// full and empty conditions.
//
// Architecture:
//   - wr_ptr/rd_ptr: binary pointers, incremented on push/pop
//   - wr_gray/rd_gray: Gray-coded versions of the pointers
//   - Synchronization: each Gray pointer is passed through a 2-stage
//     synchronizer into the other domain (wr_gray_sync, rd_gray_sync)
//   - Empty: rd_gray == wr_gray_sync (read domain sees no new data)
//   - Full: wr_gray == rd_gray_sync with top two bits inverted
//     (write domain sees read pointer wrapped exactly once behind)
//   - On push (wr_en && !full): write data, advance wr_ptr
//   - On pop  (rd_en && !empty): output data, advance rd_ptr
module fifo_async(
  input        clk,
  input        reset,
  input        wr_en,
  input        rd_en,
  input  [7:0] wr_data,
  output reg [7:0] rd_data,
  output reg   full,
  output reg   empty
);
  reg [7:0] mem [0:7];
  reg [3:0] wr_ptr, rd_ptr;
  reg [3:0] wr_gray, rd_gray;
  reg [3:0] wr_gray_sync, rd_gray_sync;
  reg [3:0] wr_gray_s1, rd_gray_s1;

  initial begin
    wr_ptr = 0; rd_ptr = 0;
    wr_gray = 0; rd_gray = 0;
    wr_gray_sync = 0; rd_gray_sync = 0;
    wr_gray_s1 = 0; rd_gray_s1 = 0;
    rd_data = 0; full = 0; empty = 1;
    mem[0] = 0; mem[1] = 0; mem[2] = 0; mem[3] = 0;
    mem[4] = 0; mem[5] = 0; mem[6] = 0; mem[7] = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      wr_ptr <= 0; rd_ptr <= 0;
      wr_gray <= 0; rd_gray <= 0;
      wr_gray_sync <= 0; rd_gray_sync <= 0;
      wr_gray_s1 <= 0; rd_gray_s1 <= 0;
      rd_data <= 0; full <= 0; empty <= 1;
    end else begin
      // Write logic
      if (wr_en && !full) begin
        mem[wr_ptr[2:0]] <= wr_data;
        wr_ptr <= wr_ptr + 4'd1;
      end

      // Read logic
      if (rd_en && !empty) begin
        rd_data <= mem[rd_ptr[2:0]];
        rd_ptr  <= rd_ptr + 4'd1;
      end

      // Gray encode pointers
      wr_gray <= wr_ptr ^ (wr_ptr << 1);
      rd_gray <= rd_ptr ^ (rd_ptr >> 1);

      // 2-stage synchronizer for write-to-read domain
      wr_gray_s1   <= wr_gray;
      wr_gray_sync <= wr_gray_s1;

      // Synchronizer for read-to-write domain (single stage)
      rd_gray_sync <= rd_gray; // HINT: check this line carefully

      // Full detection: compare synced pointers with top bits inverted
      full <= (wr_gray_sync == {~rd_gray[3:2], rd_gray[1:0]}); // HINT: check this line carefully

      // Empty detection
      empty <= (rd_gray == wr_gray_sync);
    end
  end

  p_reset:          assert property (@(posedge clk) reset |=> empty && !full && wr_ptr == 4'd0 && rd_ptr == 4'd0);
  p_gray_encode:    assert property (@(posedge clk) !reset |=> wr_gray == ($past(wr_ptr) ^ ($past(wr_ptr) >> 1)));
  p_full_detect:    assert property (@(posedge clk) !reset && wr_gray == {~rd_gray_sync[3:2], rd_gray_sync[1:0]} |=> full);
  p_empty_detect:   assert property (@(posedge clk) !reset && rd_gray == wr_gray_sync |=> empty);
  p_sync_delay:     assert property (@(posedge clk) !reset |=> wr_gray_s1 == $past(wr_gray) && wr_gray_sync == $past(wr_gray_s1));
  p_no_overflow:    assert property (@(posedge clk) !reset && full |-> !(wr_en && (wr_ptr != $past(wr_ptr))));
  p_data_integrity: assert property (@(posedge clk) !reset && rd_en && !empty |=> rd_data == $past(mem[$past(rd_ptr[2:0])]));
endmodule
