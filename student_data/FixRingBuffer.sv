// Ring buffer (FIFO) with 4 entries.
// The buffer has multiple bugs in pointer advancement and count tracking.
module ring_buffer(input clk, input reset,
                   input wr_en, input rd_en,
                   input [7:0] din, output reg [7:0] dout,
                   output reg [2:0] count,
                   output full, output empty);
  reg [7:0] mem [0:3];
  reg [1:0] wr_ptr, rd_ptr;

  assign full  = (count >= 3);
  assign empty = (count == 0);

  initial begin
    count  = 0;
    wr_ptr = 0;
    rd_ptr = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      count  <= 0;
      wr_ptr <= 0;
      rd_ptr <= 0;
    end else begin
      if (wr_en && !full) begin
        mem[wr_ptr] <= din;
        count       <= count + 1;
      end
      if (rd_en && !empty) begin
        dout   <= mem[rd_ptr];
        rd_ptr <= rd_ptr + 1;
        count  <= count + 1;
      end
    end
  end

  p_noover:    assert property (@(posedge clk) count <= 4);
  p_rd_dec:    assert property (@(posedge clk) !reset && rd_en && !empty && !wr_en |=> count == $past(count) - 1);
  p_wr_inc:    assert property (@(posedge clk) !reset && wr_en && !full && !rd_en |=> count == $past(count) + 1);
  p_wr_ptr:    assert property (@(posedge clk) !reset && wr_en && !full |=> wr_ptr == ($past(wr_ptr) + 2'b1));
endmodule
