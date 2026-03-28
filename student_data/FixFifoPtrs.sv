// Synchronous 8-entry FIFO with occupancy tracking.
//
// Write pointer (wr_ptr) and read pointer (rd_ptr) each advance by 1
// (wrapping 7→0) on each successful write/read.
// 'count' tracks the number of entries currently in the FIFO.
// full  when count == 8.
// empty when count == 0.
//
// Three wiring bugs corrupt the write addressing, read pointer update, and empty detection.
module fifo8(
  input  clk,
  input  reset,
  input  wr_en,
  input  [7:0] din,
  input  rd_en,
  output reg [7:0] dout,
  output full,
  output empty
);
  reg [7:0] mem [0:7];
  reg [2:0] wr_ptr;
  reg [2:0] rd_ptr;
  reg [3:0] count;

  initial begin wr_ptr = 0; rd_ptr = 0; count = 0; dout = 0; end

  assign full  = (count == 4'd8);
  assign empty = (count == 4'd1);

  always @(posedge clk) begin
    if (reset) begin
      wr_ptr <= 3'd0;
      rd_ptr <= 3'd0;
      count  <= 4'd0;
      dout   <= 8'h00;
    end else begin
      if (wr_en && !full) begin
        mem[rd_ptr] <= din;
        wr_ptr      <= wr_ptr + 1;
        count       <= count + 1;
      end
      if (rd_en && !empty) begin
        dout   <= mem[rd_ptr];
        rd_ptr <= wr_ptr + 1;
        count  <= count - 1;
      end
    end
  end

  p_reset:      assert property (@(posedge clk) reset |=> empty && !full && count == 4'd0);
  p_count_wr:   assert property (@(posedge clk) !reset && wr_en && !full && !rd_en |=> count == ($past(count) + 4'd1));
  p_count_rd:   assert property (@(posedge clk) !reset && rd_en && !empty && !wr_en |=> count == ($past(count) - 4'd1));
  p_count_rw:   assert property (@(posedge clk) !reset && wr_en && rd_en && !full && !empty |=> count == $past(count));
  p_data_rt:    assert property (@(posedge clk) !reset && wr_en && !full && din==8'hA5 && count==4'd0 ##1 !reset && rd_en && !empty |=> reset || dout == 8'hA5);
  p_wr_ptr_inc: assert property (@(posedge clk) !reset && wr_en && !full |=> wr_ptr == ($past(wr_ptr) + 3'd1));
  p_rd_ptr_inc: assert property (@(posedge clk) !reset && rd_en && !empty |=> rd_ptr == ($past(rd_ptr) + 3'd1));
endmodule
