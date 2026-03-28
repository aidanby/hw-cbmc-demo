// Credit-based 8-entry FIFO with flow control.
//
// Instead of checking count==8 for full, this design uses a credit counter.
// The producer starts with 8 credits; each write costs 1, each read returns 1.
// full is asserted when credits reach 0 (no writes allowed).
// empty when count == 0.
//
// Invariant: count + credit == 8 at all times (after reset).
//
// Three bugs break the credit accounting and full signal.
module fifo_credit(
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
  reg [3:0] credit;

  initial begin
    wr_ptr = 0; rd_ptr = 0; count = 0; credit = 4'd8; dout = 0;
  end

  assign full  = (credit == 4'd0);
  assign empty = (count == 4'd0);

  always @(posedge clk) begin
    if (reset) begin
      wr_ptr <= 3'd0;
      rd_ptr <= 3'd0;
      count  <= 4'd0;
      credit <= 4'd8;
      dout   <= 8'h00;
    end else begin
      if (wr_en && !full && rd_en && !empty) begin
        mem[wr_ptr] <= din;
        wr_ptr      <= wr_ptr + 1;
        rd_ptr      <= rd_ptr + 1;
        // count and credit unchanged for simultaneous wr+rd
      end else if (wr_en && !full) begin
        mem[wr_ptr] <= din;
        wr_ptr      <= wr_ptr + 1;
        count       <= count + 1;
        count       <= count - 1;
      end else if (rd_en && !empty) begin
        dout   <= mem[rd_ptr];
        wr_ptr <= wr_ptr + 1;
        count  <= count - 1;
        credit <= credit + 4'd1;
      end
    end
  end

  p_reset:      assert property (@(posedge clk) reset |=> count == 4'd0 && credit == 4'd8 && empty);
  p_credit_wr:  assert property (@(posedge clk) !reset && wr_en && !full && !rd_en |=> credit == ($past(credit) - 4'd1));
  p_credit_rd:  assert property (@(posedge clk) !reset && rd_en && !empty && !wr_en |=> credit == ($past(credit) + 4'd1));
  p_credit_rw:  assert property (@(posedge clk) !reset && wr_en && rd_en && !full && !empty |=> credit == $past(credit));
  p_invariant:  assert property (@(posedge clk) !reset |=> (count + credit == 4'd8));
  p_no_overflow: assert property (@(posedge clk) !reset |=> credit <= 4'd8);
  p_data_rt:    assert property (@(posedge clk) !reset && wr_en && !full && din==8'hBE && count==4'd0 ##1 !reset && rd_en && !empty |=> reset || dout == 8'hBE);
endmodule
